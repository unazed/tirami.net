# pylint: disable=missing-module-docstring, missing-function-docstring
# pylint: disable=missing-class-docstring
from urllib.parse import urlparse, parse_qsl
from http.cookies import SimpleCookie
from html import escape
import base64
import hashlib
import inspect
import os
import sys
import time
import types
import pprint
import htmlmin
import zlib
from .socket_server import SocketServer


_print = print


def print(*args, **kwargs):  # pylint: disable=redefined-builtin
    prev_fn = inspect.currentframe().f_back.f_code.co_name
    _print(f"[{time.strftime('%H:%M:%S')}] [HttpsServer] [{prev_fn}]",
           *args, **kwargs)


def proxy_print(arg):
    _print(repr(arg))
    return arg


def global_exception_handler(exctype, value, traceback):
    print(f"exception caught, reason: {value!r}")
    sys.__excepthook__(exctype, value, traceback)


sys.excepthook = global_exception_handler


def fulfill_websocket_extensions(extension, params):
    print(params)
    if extension == "permessage-deflate":
        for idx, param in enumerate(params):
            if "client_max_window_bits" in param:
                del params[idx]
        params.append(f"server_max_window_bits={zlib.MAX_WBITS}")
        params.append(f"client_max_window_bits={zlib.MAX_WBITS}")


def parse_websocket_parameters(params):
    if not params:
        return []
    result = []
    for param in params:
        if '=' in param:
            result.append(param.split("=", 1).strip())
        else:
            result.append(param.strip())
    return result


def parse_websocket_extensions(extensions):
    results = {}
    for ext in extensions.split(","):
        name, *params = ext.split(";")
        results[name.strip()] = parse_websocket_parameters(params)
    return results


class HttpsServer(SocketServer):
# <editor-fold HttpsServer Constants
    HTTP_VERSION = (1, 1)
    HTTP_STATUSES = {
        "Switching Protocols": 101,
        "OK": 200,
        "Moved Permanently": 301,
        "Redirect": 301,
        "Bad Request": 400,
        "Forbidden": 403,
        "Not Found": 404,
        "Method Not Allowed": 405,
        "Upgrade Required": 429,
        "Internal Error": 500,
        "HTTP Version Unsupported": 505
        }
    DEFAULT_ERROR_FORMAT = """
    <html>
        <head>
            <title>{reason}</title>
        </head>
        <body>
            <h1>{code} - {reason}</h1>
            <hr>
            <p>{body}</p>
        </body>
    </html>
    """
    SERVER_NAME = "UnazedHttpd"
    SUPPORTED_PROTS = ("websocket",)

    WEBSOCKET_VERSION = "13"
    WEBSOCKET_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    WEBSOCKET_SUPPORTED_EXTS = ("permessage-deflate",)
# </editor-fold>
# <editor-fold __init__
    def __init__(self, *args, root_directory="./", minify_data=True,
                 callbacks=None, **kwargs):
        print("initializing HttpsServer instance, and subclasses")
        if not os.path.exists(root_directory):
            raise OSError(f"{root_directory!r} doesn't exist")
        self.root_directory = root_directory
        self.callbacks = callbacks or {}
        self.routes = {}

        self.websocket_clients = []

        minifier = htmlmin.Minifier()
        self.minify = minifier.minify if minify_data else lambda data: data

        super().__init__(*args, **kwargs)
# </editor-fold>
# <editor-fold retrieve_route
    def retrieve_route(self, path, *, try_wildcard=True):
        uri = urlparse(path)
        if uri.path not in self.routes:
            if try_wildcard and (route := self.routes.get("/*")) is not None:
                route = route.copy()
                route.update({"path": uri.path})
                return (route, dict(parse_qsl(uri.query)))
            return (None, None)
        return (self.routes[uri.path], dict(parse_qsl(uri.query)))
# </editor-fold>
# <editor-fold route
    def route(self, methods, path, get_params=None, *,
              ignore_redundant_params=True, enforce_params=True,
              protocol_handler=None):
        def create_route(function):
            print(f"registered {path!r}")
            self.routes[path] = {
                "methods": methods if isinstance(methods, (list, tuple))
                                   else [methods],
                "function": function,
                "get_params": get_params or [],
                "options": {
                    "ignore_redundant_params": ignore_redundant_params,
                    "enforce_params": enforce_params,
                    "protocol_handler": function if protocol_handler is None
                                                 else protocol_handler
                    },
                "path": path
                }
        return create_route
# </editor-fold>
# <editor-fold on_data_received
    def on_data_received(self, server, addr, data):
        try:
            headers, content = data.split(b"\r\n\r\n", maxsplit=1)
        except ValueError:
            print(f"malformed request, {data[:100]!r}")
            server.trans.write(self.construct_response("Bad Request"),
                error_body="<p>Malformed request</p>"
                )
            server.trans.close()
            return
        method, headers = self.interpret_headers(headers)
        if method['version'] != HttpsServer.HTTP_VERSION:
            print(f"unsupported HTTP version, {method['version']}")
            server.trans.write(self.construct_response("HTTP Version Unsupported"),
                error_body="<p>Unsupported HTTP protocol version</p>"
                )
            server.trans.close()
            return

        # parse cookies
        cookies = {}
        for k, v in SimpleCookie(headers.get("cookie")).items():
            cookies[k] = v.value

        # retrieve and error-check route validity
        route, query_string = self.retrieve_route(method['path'])
        if route is None:  # pylint: disable=no-else-return
            print(f"route {method['path'][:20]!r} not found")
            server.trans.write(self.construct_response("Not Found",
                error_body=f"<p>Path {escape(method['path'])} not found</p>"
                ))
            server.trans.close()
            return
        elif method['method'] not in route['methods']:
            if "upgrade" not in headers:
                print(f"invalid method {method['method']}")
                server.trans.write(self.construct_response("Method Not Allowed",
                    error_body="<p>Unsupported method, this page only allows "
                               f"({', '.join(method['method'])})-requests</p>"
                    ))
                server.trans.close()
                return

        # guarantee route certain assumptions
        if not route['options']['ignore_redundant_params']:
            if any(k not in route['get_params'] for k in query_string):
                print("'ignore_redundant_params' not satisfied")
                server.trans.write(self.construct_response("Bad Request",
                    error_body="<p>Extraneous GET parameters found, this page "
                               "enforces against this</p>"
                    ))
                server.trans.close()
                return
        if route['options']['enforce_params']:
            if not all(k in query_string for k in route['get_params']):
                print("'enforce_params' not satisfied")
                server.trans.write(self.construct_response("Bad Request",
                    error_body="<p>The GET parameters "
                               f"({', '.join(route['get_params'])}) for this "
                               "page are mandatory</p>"
                    ))
                server.trans.close()
                return

        metadata = {
            "transport": server.trans,
            "cookies": cookies,
            "method": method,
            "headers": headers,
            "body": content
            }

        # upgrade connection, if necessary
        if "upgrade" in headers.get("connection").lower():
            if (upgrade_method := headers.get("upgrade")) is None:
                server.trans.write(self.construct_response("Bad Request",
                    error_body="<p>Connection requested to be upgraded, "
                               "but no Upgrade header</p>"
                    ))
                server.trans.close()
                return
            elif upgrade_method not in HttpsServer.SUPPORTED_PROTS:
                server.trans.write(self.construct_response("Bad Request",
                    error_body="<p>Unsupported upgrade protocol</p>"
                    ))
                server.trans.close()
                return
            elif upgrade_method not in route['methods']:
                server.trans.write(self.construct_response("Bad Request",
                    error_body="<p>Tried to upgrade with unsuitable method</p>"
                    ))
                server.trans.close()
                return  # goofy chain of repetition, tbd
            upgrade_fn = getattr(self, f"upgrade_to_{upgrade_method}", None)
            if upgrade_fn is None:
                server.trans.write(self.construct_response("Internal Error",
                    error_body="<p>Upgrade bootstrap defined, but not "
                               "implemented</p>"
                    ))
                server.trans.close()
                return
            print(f"upgrading connection to {upgrade_method!r}")
            upgrade_fn(metadata)
            return
            # this doesn't necessarily mean failure
        print(f"{method['method']} {method['path']}")
        resp = route['function'](
            metadata,
            **{k: v for k, v in query_string.items()
               if k in route['get_params']}
            )
        if resp is None:
            server.trans.close()
        elif resp.get("close", False):
            server.trans.close()
# </editor-fold>
# <editor-fold upgrade_to_websocket
    def upgrade_to_websocket(self, metadata):
        trans = metadata['transport']
        headers = metadata['headers']
        method = metadata['method']
        agreed_extensions = {}
        if (websocket_key := headers.get("sec-websocket-key")) is None:
            print("'sec-websocket-key' wasn't passed")
            trans.close()
            return False
        elif (websocket_version := headers.get("sec-websocket-version")) is None:
            print("'sec-websocket-version' wasn't passed")
            trans.close()
            return False
        elif websocket_version != HttpsServer.WEBSOCKET_VERSION:
            print(f"'sec-websocket-version = {websocket_version}' unsupported")
            trans.write(self.construct_response("Upgrade Required", {
                "sec-websocket-version": HttpsServer.WEBSOCKET_VERSION
                }))
            trans.close()
            return False
        elif (extensions := headers.get("sec-websocket-extensions")) is not None:
            for ext, params in parse_websocket_extensions(extensions).items():
                if ext not in HttpsServer.WEBSOCKET_SUPPORTED_EXTS:
                    print(f"unsupported websocket extension {ext!r} skipped")
                    continue
                print(f"agreed WS extension {ext!r} with params: {params!r}")
                fulfill_websocket_extensions(ext, params)
                agreed_extensions[ext] = params
        print("successfully upgraded connection")
        accept_hash = base64.b64encode(hashlib.sha1(
            (websocket_key + HttpsServer.WEBSOCKET_MAGIC).encode()
            ).digest()).decode()
        data = {
            "connection": "Upgrade",
            "upgrade": "websocket",
            "sec-websocket-accept": accept_hash
        }
        if agreed_extensions:
            data.update({
                "sec-websocket-extensions": ', '.join(
                    f"{ext}" + ("; " + '; '.join(params) if params else "") for ext, params in agreed_extensions.items()
                )
            })
            print("LOOL", data)
        trans.write(self.construct_response("Switching Protocols", data))
        self.websocket_clients.append(trans)
        prot = trans.get_protocol()
        prot.on_data_received = lambda *args:\
            self.routes[metadata['method']['path']]\
                ['options']['protocol_handler'](
                    len(self.websocket_clients)-1, agreed_extensions, *args
                )
        return False
# </editor-fold>
# <editor-fold construct_response
    def construct_response(self, reason, headers=None, body="",
                           *, add_content_length=True,
                           add_server_header=True, error_body=None,
                           do_minify=True):
        if do_minify:
            body = self.minify(body).strip()

        if headers is None:
            headers = ""
        else:
            headers = '\r\n'.join(
                f"{header}: {field}" if isinstance(field, str) else
                '\r\n'.join(
                    f"{header}: {subfield}"
                    for subfield in field
                )  # e.g. multiple Set-Cookie headers
                for header, field in headers.items()
                ) + "\r\n"

        if isinstance((status := HttpsServer.HTTP_STATUSES[reason]), (tuple, list)):
            print(f"fetching {status[1]!r}")
            code, body = status[0], self.read_file(status[1])
        elif error_body is not None:
            body = HttpsServer.DEFAULT_ERROR_FORMAT.format(
                code=status, reason=reason, body=error_body
                )
            code = status
        else:
            code = status

        if add_content_length:
            headers += f"Content-length: {len(body)}\r\n"
        if add_server_header:
            headers += f"Server: {self.SERVER_NAME}\r\n"
        headers += "\r\n"

        return (f"HTTP/{'.'.join(map(str, HttpsServer.HTTP_VERSION))} " +
                f"{code} {reason}\r\n" +
                headers).encode() +\
                (body.encode() if isinstance(body, str) else body)  # noqa: E127
# </editor-fold>
# <editor-fold register_error_handler
    def register_error_handler(self, code, filename):
        if not os.path.isfile(f"{self.root_directory}/{filename}"):
            print(f"tried to register {code}@{filename!r}, but failed")
            return False
        for k, v in HttpsServer.HTTP_STATUSES.items():
            if isinstance(v, (list, tuple)) and v[0] == code:
                print(f"already registered {code}@{filename}")
                return False
            elif v == code:
                break
        else:
            print(f"code {code} doesn't exist")
            return False
        HttpsServer.HTTP_STATUSES[k] = (code, filename)
        print(f"registered {code}@{filename!r}")
        return True
# </editor-fold>
# <editor-fold interpret_headers
    @staticmethod
    def interpret_headers(headers):
        # pylint: disable=bad-continuation
        if isinstance(headers, bytes):
            headers = headers.decode()
        method_line, *headers = headers.split("\r\n")
        method = {}

        try:
            method, path, version = method_line.split()
            version = tuple(map(int,
                                version.split("/")[1]
                                       .split(".")
                                ))
            method = {
                "method": method,
                "path": path,
                "version": version
                }
        except ValueError:
            return False

        header_dict = {}
        for header in headers:
            try:
                field, value = header.split(":", maxsplit=1)
                field = field.lower()
                value = value.strip()
            except ValueError:
                return False
            if not value:  # pylint: disable=no-else-return
                return False
            elif field in header_dict:
                if isinstance(header_dict[field], str):
                    header_dict[field] = [header_dict[field], value]
                else:
                    header_dict[field].append(value)
                continue
            header_dict[field] = value

        return method, header_dict
# </editor-fold>
# <editor-fold handle_requests
    async def handle_requests(self):
        print("registering async. handlers and then handling requests")
        if not self.routes:
            print("no routes are registered")
            return
        await self.handle_connections(
            on_data_received=self.on_data_received,
            **self.callbacks
            )
# </editor-fold>
# <editor-fold read_file
    def read_file(self, name, default=None, format=None, read_kwargs={}):
        if isinstance(name, types.FunctionType):
            name = name(self)
        if not os.path.isfile(path := f"{self.root_directory}/{name}"):
            if default is None:
                return ""
            with open(f"{self.root_directory}/{default}", **read_kwargs) as out:
                return out.read()
        with open(path, **read_kwargs) as out:
            data = out.read()
            if isinstance(format, dict):
                for k, v in format.items():
                    data = data.replace(k, v)
            return data
# </editor-fold>
# <editor-fold send_file
    def send_file(self, metadata, filename, status="OK", *, headers=None,
                  format=None, read_kwargs={}, **kwargs):
        metadata['transport'].write(self.construct_response(
                status, headers, self.read_file(
                    filename, format=format,
                    read_kwargs=read_kwargs
                    ),
                **kwargs
            ))
# </editor-fold>
# <editor-fold Test code
if __name__ == "__main__":
    class WebsocketClient:
        def __init__(self, trans, addr):
            self.trans = trans
            self.addr = addr
        def __call__(self, trans, addr, data):
            print("got", data)

    server = HttpsServer(
        root_directory="html/",
        host="", port=6969,
        cert_chain=".ssl/tirami.net.pem",
        priv_key=".ssl/tirami.net.key"
        )

    clients = {}


    @server.route("websocket", "/")
    def index(idx, prot, addr, data):
        print("registering new transport")
        if idx not in clients:
            clients[idx] = WebsocketClient(prot.trans, addr)
        prot.on_data_received = clients[idx]

    async def main():
        await server.handle_requests()


    try:
        server.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("exiting...")
    finally:
        server.loop.close()
# </editor-fold>

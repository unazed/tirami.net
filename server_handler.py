from html import escape
import base64
import hashlib
import time
import inspect
import ipaddress
import os
import json
import string
import types
import server_constants
import server_utils
import server_api.websocket_interface
from server_api.https_server import HttpsServer
from server_api.websocket_interface import WebsocketPacket, CompressorSession


class WebsocketClient:
    def __init__(self, extensions, server, trans, addr):
        server_api.websocket_interface.EXTENSIONS = extensions
        self.trans = trans
        self.addr = addr

        self.server = server
        comp = None

        self.comp = None
        if (params := extensions.get("permessage-deflate")) is not None:
            if (wbits := params.get("server_max_window_bits")) is None:
                self.comp = CompressorSession()
            else:
                self.comp = CompressorSession(int(wbits))
            print("creating compression object, wbits =", wbits)
        self.packet_ctor = WebsocketPacket(None, self.comp)

        self.authentication = server.authentication = {}
        self.chat_initialized = False
        self.__is_final = True
        self.__data_buffer = ""

    def broadcast_message(self, message_obj):
        if not self.chat_initialized:
            return
        for ws_client in self.server.clients.values():
            if not ws_client.chat_initialized:
                continue
            ws_client.trans.write(ws_client.packet_ctor.construct_response({
                "action": "on_message",
                "message": message_obj
            }))

    def __call__(self, prot, addr, data):
        if self.authentication and self.authentication['username'] not in self.server.logins:
            self.authentication = {}
            self.trans.write(self.packet_ctor.construct_response({
                "error": "username doesn't exist anymore"
            }))
        elif self.authentication and self.authentication['token'] != \
                self.server.logins[self.authentication['username']]['active_token']:
            self.authentication = {}
            self.trans.write(self.packet_ctor.construct_response({
                "error": "expired/invalid token"
            }))
        if self.__data_buffer:
            data = self.__data_buffer
        data = self.packet_ctor.parse_packet(data)
        if data['extra']:
            print("leading packet found, parsing and processing")
            self.__call__(prot, addr, data['extra'])
        self.__is_final = data['is_final']
        if not self.__is_final:
            print("receiving data fragments")
            self.__data_buffer += data['data']
            return
        elif self.__data_buffer:
            data = self.packet_ctor.parse_packet(self.__data_buffer + data['data'])
            self.__data_buffer = ""
            print("finished receiving, length =", len(data['data']))

        if data['opcode'] == 0x08:
            print("received close frame")
            self.trans.close()
            return
        elif data['opcode'] == 0x01:
            try:
                content = json.loads(data['data'])
            except json.JSONDecodeError as exc:
                self.trans.write(self.packet_ctor.construct_response({
                    "error": "client sent invalid JSON"
                }))
                return

            if (action := content.get("action")) is None:
                self.trans.write(self.packet_ctor.construct_response({
                    "error": "no 'action' passed"
                }))
                return
            elif action not in server_constants.SUPPORTED_WS_ACTIONS:
                self.trans.write(self.packet_ctor.construct_response({
                    "error": f"action {escape(action)!r} doesn't exist"
                }))
                return

            if action == "event_handler":
                if not (event_name := server_utils.ensure_contains(
                        self, content, ("name",)
                        )):
                    return
                event_name = event_name[0]
                if (event := server_constants.SUPPORTED_WS_EVENTS.get(event_name)) is None:
                    self.trans.write(self.packet_ctor.construct_response({
                        "error": f"event {escape(event_name)!r} not registered"
                    }))
                    return
                elif isinstance(event, types.FunctionType):
                    event = event(self)
                data = self.server.read_file(event, format={
                    "$$username": '"' + self.authentication.get("username", "") + '"',
                    "$$auth_token": '"' + self.authentication.get("token", "") + '"'
                })
                if not data:
                    self.trans.write(self.packet_ctor.construct_response({
                        "warning": f"{event_name!r} unimplemented"
                    }))
                    return
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "do_load",
                    "data": data
                }))
                if "navigation" not in event:  #smh
                    print(f"retrieving event {event!r}")
            elif action == "register":
                if self.authentication:
                    self.trans.write(self.packet_ctor.construct_response({
                        "error": "you're already logged in"
                    }))
                    return
                elif not (res := server_utils.ensure_contains(
                        self.trans, content, ("username", "password")
                        )):
                    self.trans.write(self.packet_ctor.construct_response({
                        "error": "either 'username' or 'password' wasn't passed"
                    }))
                    return
                username, password = res
                if username in server.logins:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['register_fail'],
                            format={
                                "$$object": "username",
                                "$$reason": '"username exists"'
                            }
                        )
                    }))
                    return
                elif not username or any(
                    c not in string.ascii_letters + string.digits + "_" for c in username
                    ):
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['register_fail'],
                            format={
                                "$$object": "username",
                                "$$reason": '"username must be [a-zA-Z0-9_]"'
                            }
                        )
                    }))
                    return
                elif not (1 < len(username) < 16):
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['register_fail'],
                            format={
                                "$$object": "username",
                                "$$reason": '"username must be between 2 and 15 characters"'
                            }
                        )
                    }))
                    return
                elif not (4 < len(password) < 16):
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['register_fail'],
                            format={
                                "$$object": "password",
                                "$$reason": '"password must be between 5 and 15 characters"'
                            }
                        )
                    }))
                    return
                password = hashlib.sha224(password.encode()).digest()
                server.logins[username] = {
                    "registration_timestamp": time.strftime("%D %H:%M:%S"),
                    "active_token": (tok := base64.b64encode(os.urandom(32)).decode()),
                    "password": base64.b64encode(password).decode()
                }
                self.authentication = {
                    "username": username,
                    "token": tok
                }
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "registered",
                    "data": {
                        "username": username,
                        "token": tok
                    }
                }))
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "do_load",
                    "data": server.read_file(
                        server_constants.SUPPORTED_WS_EVENTS['home'],
                        format={
                            "$$username": f'"{username}"',
                            "$$auth_token": f'"{tok}"'
                            }
                        )
                }))
                self.broadcast_message({
                    "username": username,
                    "content": escape(f"registered new account")
                })
                server_utils.commit_logins(self.server)
            elif action == "login":
                if self.authentication:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['login_fail'],
                            format={
                                "$$object": "null",
                                "$$reason": '"already logged in"'
                            }
                        )
                    }))
                    return
                elif (tok := content.get("token")):
                    for user, data in server.logins.items():
                        if data['active_token'] == tok:
                            break
                    else:
                        self.trans.write(self.packet_ctor.construct_response({
                            "action": "do_load",
                            "data": self.server.read_file(
                                server_constants.SUPPORTED_WS_EVENTS['login_fail'],
                                format={
                                    "$$object": "null",
                                    "$$reason": '"no such token exists"'
                                }
                            )
                        }))
                        return
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "login",
                        "data": {
                            "username": user
                        }
                    }))
                    self.authentication = {
                        "username": user,
                        "token": tok
                    }
                    print(f"{user!r} logged in via token")
                    self.broadcast_message({
                        "username": user,
                        "content": escape(f"logged in with token")
                    })
                    return
                if not (res := server_utils.ensure_contains(
                        self.trans, content, ("username", "password")
                        )):
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['login_fail'],
                            format={
                                "$$object": "null",
                                "$$reason": '"either \'username\' or \'password\' wasn\'t passed"'
                            }
                        )
                    }))
                    return
                username, password = res
                if username not in self.server.logins:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['login_fail'],
                            format={
                                "$$object": "username",
                                "$$reason": '"no such username exists"'
                            }
                        )
                    }))
                    return
                password = base64.b64encode(hashlib.sha224(password.encode()).digest()).decode()
                for user, data in self.server.logins.items():
                    if data['password'] == password:
                        break
                else:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "do_load",
                        "data": self.server.read_file(
                            server_constants.SUPPORTED_WS_EVENTS['login_fail'],
                            format={
                                "$$object": "password",
                                "$$reason": '"password mismatch"'
                            }
                        )
                    }))
                    return
                print(f"{username!r} logged in manually")
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "login",
                    "data": {
                        "username": username,
                        "token": (tok := base64.b64encode(os.urandom(32)).decode())
                    }
                }))
                self.authentication = {
                    "username": username,
                    "token": tok
                }
                self.server.logins[username].update({
                    "active_token": tok
                })
                self.broadcast_message({
                    "username": username,
                    "content": escape(f"logged in")
                })
                server_utils.commit_logins(self.server)
            elif action == "logout":
                if not self.authentication:
                    self.trans.write(self.packet_ctor.construct_response({
                        "error": "tried to logout when not logged in"
                    }))
                    return

                self.server.logins[self.authentication['username']]['active_token'] = ""
                print(f"{self.authentication['username']!r} logged out")
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "do_load",
                    "data": self.server.read_file(
                        server_constants.SUPPORTED_WS_EVENTS['logout']
                        )
                }))
                self.trans.write(self.packet_ctor.construct_response({
                    "action": "do_load",
                    "data": self.server.read_file(
                        server_constants.SUPPORTED_WS_EVENTS['home'],
                        format={
                            "$$username": '""',
                        }
                    )
                }))
                self.broadcast_message({
                    "username": self.authentication['username'],
                    "content": "logged out"
                })
                self.authentication = {}
            elif action == "initialize_chat":
                if self.chat_initialized:
                    return
                self.chat_initialized = True
                username = self.authentication.get("username", "Guest")
                self.broadcast_message({
                    "username": "SYSTEM",
                    "content": escape(
                        f"{username} joined"
                        )
                })
            elif action == "send_message":
                if not (message := server_utils.ensure_contains(
                        self, content, ("message",)
                        )):
                    return
                message = message[0]
                if not self.authentication:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "on_message",
                        "message": {
                            "username": "SYSTEM",
                            "content": "register or login to post a message"
                        }
                    }))
                    return
                elif len(message) > 255:
                    self.trans.write(self.packet_ctor.construct_response({
                        "action": "on_message",
                        "message": {
                            "username": "SYSTEM",
                            "content": "message must be less than 256 characters"
                        }
                    }))
                    return
                print(f"{self.authentication['username']}: {message!r}")
                self.broadcast_message({
                    "username": self.authentication['username'],
                    "content": escape(message)
                })
        else:
            print("received weird opcode, closing for inspection",
                    hex(data['opcode']))
            self.trans.close()

    def on_close(self, prot, addr, reason):
        print(f"closed websocket with {addr[0]!r}, reason={reason!r}")

_print = print


def print(*args, **kwargs):  # pylint: disable=redefined-builtin
    curframe = inspect.currentframe().f_back
    prev_fn = curframe.f_code.co_name
    class_name = ""
    if (inst := curframe.f_locals.get("self")) is not None:
        class_name = f" [{inst.__class__.__name__}]"
    _print(f"[{time.strftime('%H:%M:%S')}] [ServerHandler]{class_name} [{prev_fn}]",
           *args, **kwargs)


async def main_loop(server):
    await server.handle_requests()


def preinit_whitelist(server, addr):
    ip = ipaddress.ip_address(addr[0])
    if not any(ip in net for net in server_constants.WHITELISTED_RANGES):
        print(f"prevented {addr[0]} from connecting due to whitelist")
        server.trans.close()
        return


server = HttpsServer(
    root_directory="html/",
    host="", port=443,
    cert_chain=".ssl/tirami.net.pem",
    priv_key=".ssl/tirami.net.key",
    callbacks={
        "on_connection_made": preinit_whitelist
        }
    )


@server.route("GET", "/")
def index_handler(metadata):
    server.send_file(metadata, "index.html")


@server.route("GET", "/unsupported", get_params=["code"])
def unsupported_handler(metadata, code=None):
    server.send_file(metadata, "unsupported.html", format={
        "error": server_constants.ERROR_CODES.get(code,
            "The server hasn't specified a reason."
            )
        })


@server.route("websocket", "/ws-tirami")
def websocket_handler(idx, extensions, prot, addr, data):
    print("registering new websocket transport")
    if idx not in server.clients:
        server.clients[idx] = WebsocketClient(extensions, server, prot.trans, addr)
    prot.on_data_received = server.clients[idx]
    prot.on_connection_lost = server.clients[idx].on_close
    prot.on_data_received(prot.trans, addr, data)


@server.route("GET", "/*")
def wildcard_handler(metadata):
    trans = metadata['transport']
    path = metadata['method']['path'][1:].split("/")
    if len(path) >= 2:
        folder, file = '/'.join(path[:-1]), path[-1]
        if folder not in server_constants.ALLOWED_FOLDERS:
            trans.write(server.construct_response("Forbidden",
                error_body=f"<p>Folder {escape(folder)!r} isn't whitelisted</p>"
                ))
            return
        headers = {}
        if isinstance((hdrs := server_constants.ALLOWED_FOLDERS[folder]), dict):
            headers = dict(filter(lambda i: not i[0].startswith("__"), hdrs.items()))
        files = os.listdir(folder)
        if file not in files:
            trans.write(server.construct_response("Not Found",
                error_body=f"<p>File {escape(folder) + '/' + escape(file)!r} "
                           "doesn't exist</p>"
                ))
            return
        server.send_file(metadata, f"../{'/'.join(path)}", headers={
            "content-type": server_constants.get_mimetype(file),
            **headers
        }, do_minify=False,
        read_kwargs=server_constants.ALLOWED_FOLDERS[folder].get(
            "__read_params", {}
        ) if server_constants.ALLOWED_FOLDERS[folder] is not None else {
            "mode": "r"
        })
        return
    trans.write(server.construct_response("Not Found",
        error_body=f"<p>File {escape(metadata['method']['path'])!r} "
                    "doesn't exist</p>"
        ))


if not os.path.isfile("logins.db"):
    with open("logins.db", "w") as logins:
        logins.write("{}")
with open("logins.db") as logins:
    try:
        server.logins = json.load(logins)
    except json.JSONDecodeError:
        print("failed to load 'logins.db'")
        server.logins = {}

server.clients = {}
server.loop.run_until_complete(main_loop(server))

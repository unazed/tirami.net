import asyncio
import ssl
import time
import inspect


_print = print
def print(*args, **kwargs):
#    prev_fn = inspect.currentframe().f_back.f_code.co_name
#    _print(f"[{time.strftime('%H:%M:%S')}] [SocketServer] [{prev_fn}]", *args, **kwargs)
    pass

def null_coroutine(*args, **kwargs):
    pass


class ServerProtocol(asyncio.Protocol):
    def __init__(self, *,
            on_connection_made=None,
            on_data_received=None,
            on_connection_lost=None,
            on_eof_error=None,
            default=null_coroutine):
        self.on_connection_made = on_connection_made or default
        self.on_data_received   = on_data_received or default
        self.on_connection_lost = on_connection_lost or default
        self.on_eof_error       = on_eof_error or default

    def connection_made(self, trans):
        self.remote_addr = trans.get_extra_info("peername")
        self.trans = trans
        print(f"received connection from {self.remote_addr[0]}")
        self.on_connection_made(self, self.remote_addr)

    def data_received(self, data):
        print(f"data received from connection {self.remote_addr[0]}")
        self.on_data_received(self, self.remote_addr, data)

    def on_eof_error(self):
        print(f"received EOF from {self.remote_addr[0]}")
        self.on_eof_error(self, self.remote_addr)

    def connection_lost(self, exc):
        print(f"lost connection from {self.remote_addr[0]}, reason: {exc!r}")
        self.on_connection_lost(self, self.remote_addr, exc)


class SocketServer:
    def __init__(self, host, port, cert_chain, priv_key, *, loop=None, backlog=10):
        self.host = host
        self.port = port
        print(f"loading SSL context")
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(cert_chain, priv_key)
        print(f"SSL context loaded successfully")
        print(f"retrieving event loop, ")
        self.loop = loop or asyncio.new_event_loop()
        self.backlog = backlog

    async def handle_connections(self, *args, **kwargs):
        print("creating asynchronous server")
        server = await self.loop.create_server(
                protocol_factory=\
                        lambda: ServerProtocol(
                            *args, **kwargs
                            ),
                host=self.host, port=self.port,
                ssl=self.context, reuse_address=True,
                backlog=self.backlog
                )
        print(f"beginning to serve on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

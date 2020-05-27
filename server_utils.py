from html import escape
import json
from server_api.websocket_interface import WebsocketPacket


def ensure_contains(self, data, keys):
    ret = []
    for key in keys:
        if key not in data:
            self.trans.write(self.packet_ctor.construct_response({
                "error": f"no {escape(key)!r} passed"
            }))
            return False
        ret.append(data[key])
    return ret


def commit_logins(server):
    with open("logins.db", "w") as logins:
        json.dump(server.logins, logins)

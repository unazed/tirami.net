from html import escape
import json
from server_api.websocket_interface import WebsocketPacket


def ensure_contains(trans, data, keys):
    ret = []
    for key in keys:
        if key not in data:
            trans.write(WebsocketPacket.construct_response({
                "error": f"{escape(key)!r} not passed"
            }))
            return False
        ret.append(data[key])
    return ret


def commit_logins(server):
    with open("logins.db", "w") as logins:
        json.dump(server.logins, logins)

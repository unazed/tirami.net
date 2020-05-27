from ipaddress import ip_network


def get_mimetype(name):
    return MIMETYPES.get(name.split(".")[-1], "text/plain")


def when_authenticated(name, must_have_auth=False):
    def inner(client):
        if not client.authentication:
            return f"events/{name}"
        elif must_have_auth:
            return SUPPORTED_WS_EVENTS['forbidden']
        return f"events/auth/{name}"
    return inner


ERROR_CODES = {
    "400": "Websockets are unsupported on your platform "
         "consider upgrading your browser. Without websockets "
         "we would not be able to serve this webpage to you."
}

SUPPORTED_WS_ACTIONS = [
    "event_handler",
    "register",
    "login", "logout",
    "navigation"
]

SUPPORTED_WS_EVENTS = {
    "home": when_authenticated("on_load.js"),
    "navigation": "events/navigation.js",
    "login": "events/login.js",
    "login_fail": "events/input_fail.js",
    "register": "events/register.js",
    "register_fail": "events/input_fail.js",
    "logout": "events/logout.js",
    "forbidden": "events/forbidden.js"
}

MIMETYPES = {
    "js": "text/javascript",
    "css": "text/css",
    "html": "text/html",
    "ico": "image/x-icon",
    "svg": "image/svg+xml"
}

WHITELISTED_RANGES = [*map(ip_network, [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/12",
    "172.64.0.0/13",
    "131.0.72.0/22",
    "86.6.165.117/32",
    "127.0.0.0/8",
    "::1",
    "192.168.0.0/24"
    ])]

ALLOWED_FOLDERS = {
    "html/css": None,
    "html/js": None,
    "html/img": {
        "Cache-Control": "nostore",
        "__read_params": {
            "mode": "rb"
            }
        }
    }

import asyncio
import aiohttp
import string
import inspect, time


_print = print


def print(*args, **kwargs):  # pylint: disable=redefined-builtin
    curframe = inspect.currentframe().f_back
    prev_fn = curframe.f_code.co_name
    class_name = ""
    if (inst := curframe.f_locals.get("self")) is not None:
        class_name = f" [{inst.__class__.__name__}]"
    _print(f"[{time.strftime('%H:%M:%S')}] [ServerHandler]{class_name} [{prev_fn}]",
           *args, **kwargs)


async def twitchtv(usernames):
    print("in twitch.tv", usernames)
    output.append("hey")


async def snapchat(usernames):
    print("in snapchat", usernames)
    output.append("hey")


async def tiktok(usernames):
    print("in tiktok", usernames)
    return "hey"

def schedule_service(loop, service_name, usernames):
    return loop.create_task(
        globals()[''.join(
            filter(lambda c: c in string.ascii_letters, service_name.lower())
        )](usernames))

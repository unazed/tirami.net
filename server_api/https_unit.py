import asyncio
import aiohttp
import ssl
import websockets


context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations(".ssl/tirami.net.pem")


async def main():
    print("testing regular HTTPS get requests")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://127.0.0.1:6969", params={
                "a_test_param": "for your ugly face smh"
            }, cookies={
                "here_s": "a cookie!"
            }, verify_ssl=False) as test:
            resp = await test.text()
        print(f"server responded with {resp}, {test}")
    print("connecting with websockets")
    async with websockets.connect("wss://127.0.0.1:6969",
                                  ssl=context) as websocket:
        print("sending websocket data")
        await websocket.send("i love you")
        resp = await websocket.recv()
        print(f"received websocket data: {resp}")


asyncio.run(main())

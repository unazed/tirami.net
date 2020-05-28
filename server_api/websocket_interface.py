import sys
import json
import inspect
import time
import zlib


_print = print


def print(*args, **kwargs):  # pylint: disable=redefined-builtin
    prev_fn = inspect.currentframe().f_back.f_code.co_name
    _print(f"[{time.strftime('%H:%M:%S')}] [WebsocketInterface] [{prev_fn}]",
           *args, **kwargs)


EXTENSIONS = {}
ZLIB_EMPTY_BLOCK = b"\0\0\xff\xff"


class CompressorSession:
    def __init__(self, wbits=zlib.MAX_WBITS):
        self.compressor = zlib.compressobj(
            wbits=-wbits,
        )
        self.decompressor = zlib.decompressobj(
            wbits=-wbits
        )

    def inflate(self, data):
        return self.decompressor.decompress(data)\
             + self.decompressor.flush(zlib.Z_SYNC_FLUSH)

    def deflate(self, data):
        return self.compressor.compress(data)\
             + self.compressor.flush(zlib.Z_SYNC_FLUSH)


class WebsocketPacket:
    def __init__(self, data, comp_sess):
        if isinstance(data, str):
            print("data passed as string-type, data may be lost in encoding")
            data = data.encode()
        self.info = None
        if data is not None:
            self.info = self.parse_packet(bytearray(self.data))
        self.comp_sess = comp_sess

    @staticmethod
    def concatenate_bytes(arr):
        data = 0
        for b in arr:
            data |= b
            data <<= 8
        data >>= 8
        return data

    @staticmethod
    def deconcatenate_bytes(num, pad):
        data = bytearray()
        while num:
            data.append(num & 0xff)
            num >>= 8
        return data[::-1].rjust(pad, b'\x00')

    def construct_response(self, data, final=True, opcode=0x01):
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode()
        
        fin_rsv_opcode = (final << 7) | opcode
        if (param := EXTENSIONS.get("permessage-deflate")) is not None:
            fin_rsv_opcode |= 0b0100_0000
            data = self.comp_sess.deflate(data)
            if final and data.endswith(ZLIB_EMPTY_BLOCK):
                data = data[:-len(ZLIB_EMPTY_BLOCK)]
        fin_rsv_opcode = bytes([fin_rsv_opcode])

        if len(data) <= 125:
            payload = bytes([len(data)])
            length = b""
        elif 126 <= len(data) < 2**16:
            payload = b"\x7e"
            length = WebsocketPacket.deconcatenate_bytes(len(data), 2)
        elif 2**16 <= len(data) < 2**64:
            payload = b"\x7f"
            length = WebsocketPacket.deconcatenate_bytes(len(data), 8)
        else:
            raise ValueError("large packets unsupported, wtf is u doin")
        return fin_rsv_opcode + payload + length + data

    @staticmethod
    def split_bits(byte, indices):
        bits = []
        for index in indices:
            mask = 0
            for n in range(index[0], index[1]+1):
                mask |= 1 << (8 - n - 1)
            bits.append((byte & mask) >> (8 - max(index) - 1))
        return bits


    def parse_packet(self, data):
        if not isinstance(data, bytearray):
            data = bytearray(data)
        fin, rsv, opcode = self.split_bits(data.pop(0), (
            [0, 0], [1, 3], [4, 7]
        ))
        mask, length = self.split_bits(data.pop(0), (
            [0, 0], [1, 7]
        ))
        if length >= 126:
            length = self.concatenate_bytes([
                data.pop(0)
                for _ in range(2 if length == 126 else 8)
            ])
        extra = ""
        if length != len(data) - (4 if mask else 0):
            data, extra = data[:length + (4 if mask else 0)], data[length + (4 if mask else 0):]

        if mask:
            masking_key = [
                data.pop(0)
                for _ in range(4)
            ]
            data = bytearray(char ^ masking_key[idx % 4] for idx, char in enumerate(data))
        content = data
        if (param := EXTENSIONS.get("permessage-deflate")) is not None:
            max_wbits = param.get("server_max_window_bits", param.get("client_max_window_bits", 15))
            if fin:
                content += ZLIB_EMPTY_BLOCK
            content = self.comp_sess.inflate(content)
        return {
            "is_final": fin,
            "reserved": rsv ^ 0b100,
            "opcode": opcode,
            "data": content,
            "extra": extra
        }

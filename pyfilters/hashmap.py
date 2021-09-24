# -*- coding: utf-8 -*-
import hashlib
import struct

import mmh3

from pyfilters.abc import BaseHash


class PyHashMap(BaseHash):
    """
    返回字符串 hash 出来的 offset (整数)，范围 0 - self.m
    """

    def __init__(self, m: int, seed: int):
        self.m = m
        self.seed = seed

    def hash(self, value: str) -> int:
        ret = 0
        for i in range(len(value)):
            ret += self.seed * ret + ord(value[i])
        return ret % self.m


class MMH3HashMap(BaseHash):
    """
    使用 murmurhash3
    返回字符串 hash 出来的 offset (整数)，范围 0 - self.m，最大范围 0 - (2^32 - 1)
    """

    def __init__(self, m: int, seed: int):
        self.m = m
        self.seed = seed

    def hash(self, value: str) -> int:
        return mmh3.hash(value, self.seed, signed=False) % self.m


class HashlibHashMap(BaseHash):
    """
    使用 hashlib
    返回字符串 hash 出来的 offset (整数)，范围 0 - self.m，最大范围 0 - (2^32 - 1)
    """

    def __init__(self, m: int, seed: int):
        self.m = m
        self.seed = seed

    def hash(self, value: str) -> int:  # magic
        m = hashlib.sha256()
        m.update(value.encode())
        m.update(self.seed.to_bytes(4, byteorder="little"))
        return struct.unpack(">IIIIIIII", m.digest())[0] % self.m

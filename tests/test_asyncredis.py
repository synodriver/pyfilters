# -*- coding: utf-8 -*-
import os
import unittest

from redis.asyncio import Redis

from pyfilters.asyncio import (
    ChunkedRedisBloomFilter,
    CountRedisBloomFilter,
    RedisBloomFilter,
)

redis_addr = os.getenv("REDIS_ADDRESS", "localhost")
redis_password = os.getenv("REDIS_PASSWORD", "")


class TestAsyncRedisBloomFilter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = Redis(host=redis_addr, port=6379, db=0, password=redis_password)
        self.rbf = RedisBloomFilter(self.redis, "bloomfilter", 10000, 0.00001)
        self.crbf = CountRedisBloomFilter(
            self.redis, "countbloomfilter", 10000, 0.00001
        )
        self.chunkrbf = ChunkedRedisBloomFilter(
            self.redis, "chunkedbloomfilter", 1000000000, 0.00000001
        )

    async def test_add(self):
        for i in range(1000):
            await self.rbf.add(i)
            await self.crbf.add(i)
            await self.chunkrbf.add(i)
        self.assertTrue(len(self.rbf) == 1000)
        self.assertTrue(len(self.crbf) == 1000)
        self.assertTrue(len(self.chunkrbf) == 1000)
        for i in range(1000):
            self.assertTrue(await self.rbf.contains(i), f"{i}居然不在里面")
            self.assertTrue(await self.crbf.contains(i), f"{i}居然不在里面")
            self.assertTrue(await self.chunkrbf.contains(i), f"{i}居然不在里面")
        self.assertFalse(await self.rbf.contains(1001), "1001居然在里面了")
        self.assertFalse(await self.crbf.contains(1001), "1001居然在里面了")
        self.assertFalse(await self.chunkrbf.contains(1001), "1001居然在里面了")

        for i in range(1000):
            await self.crbf.remove(i)
            self.assertFalse(await self.crbf.contains(i), f"{i}居然没有被remove")
            self.assertTrue(
                len(self.crbf) == 1000 - i - 1, f"i={i}; len={len(self.crbf)}"
            )

        await self.rbf.clear()
        self.assertFalse(await self.rbf.contains(1))
        await self.crbf.clear()
        self.assertFalse(await self.crbf.contains(1))
        await self.chunkrbf.clear()
        self.assertFalse(await self.chunkrbf.contains(1))
        self.assertTrue(len(self.rbf) == 0)
        self.assertTrue(len(self.crbf) == 0)
        self.assertTrue(len(self.chunkrbf) == 0)

    def test_raise(self):
        with self.assertRaises(NotImplementedError):
            1 in self.rbf
        with self.assertRaises(NotImplementedError):
            1 in self.crbf
        with self.assertRaises(NotImplementedError):
            1 in self.chunkrbf


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
import os
import unittest

redis_addr = os.getenv("REDIS_ADDRESS", "localhost")
redis_password = os.getenv("REDIS_PASSWORD", "")

from redis import Redis

from pyfilters import ChunkedRedisBloomFilter, CountRedisBloomFilter, RedisBloomFilter


class TestRedis(unittest.TestCase):
    def setUp(self):
        self.redis = Redis(redis_addr, port=6379, db=0, password=redis_password)
        self.rbf = RedisBloomFilter(self.redis, "bloomfilter", 10000, 0.00001)
        self.rcbf = CountRedisBloomFilter(
            self.redis, "countbloomfilter", 10000, 0.00001
        )  # todo: 每个测试是独立的，属性会被deepcopy，因此测试之间不能有依赖关系

    def test_add(self):
        for i in range(1000):
            self.rbf.add(i)
            self.rcbf.add(i)
            self.assertTrue(len(self.rbf) == i + 1, f"{len(self.rbf)} {i}")
            self.assertTrue(len(self.rcbf) == i + 1, f"{len(self.rcbf)} {i}")
        for i in range(1000):
            self.assertTrue(i in self.rbf, f"{i}居然不在里面")
            self.assertTrue(i in self.rcbf, f"{i}居然不在里面")
        self.assertNotIn(1001, self.rbf, "1001居然在里面了")
        self.assertNotIn(1001, self.rcbf, "1001居然在里面了")

        for i in range(1000):
            self.rcbf.remove(i)
            self.assertNotIn(i, self.rcbf, f"{i}居然没有被remove")
            self.assertTrue(
                len(self.rcbf) == 1000 - i - 1, f"i={i}; len={len(self.rcbf)}"
            )

        self.rbf.clear()
        self.assertNotIn(1, self.rbf)
        self.rcbf.clear()
        self.assertNotIn(1, self.rcbf)


class TestChunkedRedis(unittest.TestCase):
    def setUp(self):
        self.redis = Redis(redis_addr, port=6379, db=0, password=redis_password)
        self.rbf = ChunkedRedisBloomFilter(
            self.redis, "chunkedbloomfilter", 1000000000, 0.00000001
        )
        pass

    def test_add(self):
        for i in range(1000):
            self.rbf.add(i)
        self.assertTrue(len(self.rbf) == 1000)
        for i in range(1000):
            self.assertTrue(i in self.rbf, f"{i}居然不在里面")
        self.assertNotIn(1001, self.rbf, "1001居然在里面了")

        self.rbf.clear()
        self.assertNotIn(1, self.rbf)


if __name__ == "__main__":
    unittest.main()

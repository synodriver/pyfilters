# -*- coding: utf-8 -*-
from hashlib import md5
from typing import Any, Optional, Type

from .abc import BaseBloomFilter, BaseHash
from .utils import calculation_bloom_filter
from .hashmap import MMH3HashMap


class RedisBloomFilter(BaseBloomFilter):
    """BloomFilter that uses Redis"""

    def __init__(self,
                 redis_client,
                 key: str,
                 capacity: int,
                 error_rate: Optional[float] = 0.001,
                 hash_type: Optional[Type[BaseHash]] = MMH3HashMap):
        """
        Redis简单存储 没有拆分大Key
        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        self.redis_client = redis_client  # redis server
        self.key = key

        m, k, mem, block_num = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m if m <= (1 << 32) else 1 << 32  # redis string 最大 512MB，即 2^32
        self.k = k  # number of hash functions
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]

    def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if item not in self:
            if not isinstance(item, str):
                item = str(item)
            with self.redis_client.pipeline() as pipe:
                for map_ in self.hashmaps:
                    value = map_.hash(item)
                    assert 0 <= value < self.m  # offset
                    pipe.setbit(self.key, value, 1)
                pipe.execute()
            self.count += 1
            return True
        return False

    def clear(self) -> None:
        """清空过滤器"""
        self.redis_client.delete(self.key)
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        with self.redis_client.pipeline() as pipe:
            for map_ in self.hashmaps:
                value = map_.hash(item)  # offset
                assert 0 <= value < self.m
                pipe.getbit(self.key, value)
            results = pipe.execute()
        return all(results)


class ChunkedRedisBloomFilter(BaseBloomFilter):
    """BloomFilter that uses Redis, Chunk big keys"""

    def __init__(self,
                 redis_client,
                 key: str,
                 capacity: int,
                 error_rate: Optional[float] = 0.001,
                 hash_type: Optional[Type[BaseHash]] = MMH3HashMap):
        """
        Redis简单存储 会拆分大Key
        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        self.redis_client = redis_client  # redis server
        self.key = key

        m, k, mem, block_num = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m if m <= (1 << 32) else 1 << 32  # redis string 最大 512MB，即 2^32
        self.k = k  # number of hash functions 哈希函数的个数，与种子数一样
        self.block_num = block_num  # number of memory blocks 需要的内存块数量
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]

        if block_num <= 256:
            self.value_split_num = 2  # 0-255
        else:
            self.value_split_num = 3  # 0-4095
        # 计算key的后缀，redis限制一个string 512Mb，当bitmap特别长时，可能超出限制。
        # 为了分开一个大key，需要对每个value计算后缀 因此实际key=key+':'+suffix
        # 这样，每一个value会落在不同的key上，绕过一个string只能2^32位长度(512Mb)的限制
        # 计算方式:对给定的value,计算一次md5,转换16进制，取前value_split_num位十六进制数转换10进制，对block_num取模，就是给定的后缀
        # 按照上述算法，可见，这里限制最大分key数量为4096 TODO 是否可以更高？ Redis说一个实例可以存2^32个key

    def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if item not in self:
            if not isinstance(item, str):
                item = str(item)
            redis_chunk_key = self.key + ":" + str(
                int(md5(item.encode()).hexdigest()[0:self.value_split_num],
                    16) % self.block_num)  # 计算分片key的值 后缀是:0,1...
            with self.redis_client.pipeline() as pipe:
                for map_ in self.hashmaps:
                    value = map_.hash(item)
                    assert 0 <= value < self.m  # offset
                    pipe.setbit(redis_chunk_key, value, 1)
                pipe.execute()
            self.count += 1
            return True
        return False

    def clear(self) -> None:
        """清空过滤器"""
        with self.redis_client.pipeline() as pipe:
            for i in range(self.block_num if self.block_num <= 4096 else 4096):
                pipe.delete(self.key + ":" + str(i))  # 删除自己的全部内存块
            pipe.execute()
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        redis_chunk_key = self.key + ":" + str(
            int(md5(item.encode()).hexdigest()[0:self.value_split_num], 16) % self.block_num)
        with self.redis_client.pipeline() as pipe:
            for map_ in self.hashmaps:
                value = map_.hash(item)  # offset
                assert 0 <= value < self.m
                pipe.getbit(redis_chunk_key, value)
            results = pipe.execute()
        return all(results)


class CountRedisBloomFilter(BaseBloomFilter):
    """
    BloomFilter that uses Redis, capable of remove elements
    会产生大量的key
    """

    def __init__(self,
                 redis_client,
                 key: str,
                 capacity: int,
                 error_rate: Optional[float] = 0.001,
                 hash_type: Optional[Type[BaseHash]] = MMH3HashMap):
        """
        Redis key当做counter
        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        self.redis_client = redis_client  # redis server
        self.key = key

        m, k, mem, block_num = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m if m <= (1 << 32) else 1 << 32
        self.k = k  # number of hash functions
        self.block_num = block_num
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]

    def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if item not in self:
            if not isinstance(item, str):
                item = str(item)
            with self.redis_client.pipeline() as pipe:
                for map_ in self.hashmaps:
                    value = map_.hash(item)
                    assert 0 <= value < self.m  # offset
                    pipe.incrby(self.key + ":" + str(value))
                pipe.execute()
            self.count += 1
            return True
        return False

    def remove(self, item: Any) -> bool:
        """
        删除元素
        :param item:
        :return: 是否删除
        """
        if item in self:
            if not isinstance(item, str):
                item = str(item)
            with self.redis_client.pipeline() as pipe:
                for map_ in self.hashmaps:
                    value = map_.hash(item)  # offset
                    assert 0 <= value < self.m
                    pipe.decrby(self.key + ":" + str(value))
                pipe.execute()
            self.count -= 1
            return True
        return False

    def clear(self) -> None:
        """清空过滤器"""
        counters = self.redis_client.keys(self.key + ":*")
        with self.redis_client.pipeline() as pipe:
            for key in counters:
                pipe.delete(key)
            pipe.execute()
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        with self.redis_client.pipeline() as pipe:
            for map_ in self.hashmaps:
                value = map_.hash(item)  # offset
                assert 0 <= value < self.m
                pipe.get(self.key + ":" + str(value))
            results = pipe.execute()
        return all(map(lambda x: x and int(x) > 0, results))

# -*- coding: utf-8 -*-
from hashlib import md5
from typing import Any, Optional, Type

from pyfilters.abc import BaseBloomFilter, BaseHash
from pyfilters.hashmap import MMH3HashMap
from pyfilters.utils import calculation_bloom_filter


class RedisBloomFilter(BaseBloomFilter):
    """BloomFilter that uses Redis"""

    def __init__(
        self,
        redis_client,
        key: str,
        capacity: int,
        error_rate: Optional[float] = 0.001,
        hash_type: Optional[Type[BaseHash]] = MMH3HashMap,
    ):
        """
        Redis简单存储 没有拆分大Key
        :param key: redis中的键名
        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        self.redis_client = redis_client  # type: redis.asyncio.Redis
        self.key = key

        m, k, mem, block_num = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m if m <= (1 << 32) else 1 << 32  # redis string 最大 512MB，即 2^32
        self.k = k  # number of hash functions
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]

        self._add_script = self.redis_client.register_script(
            """
            local redis_chunk_key = KEYS[1]
            for key = 2, #KEYS do
                redis.call("SETBIT", redis_chunk_key, tonumber(KEYS[key]), 1)
            end
            return {ok='OK'}
            """
        )
        self._contains_script = self.redis_client.register_script(
            """
           local redis_chunk_key = KEYS[1]
            for key = 2, #KEYS do
                local ret = redis.call("GETBIT", redis_chunk_key, tonumber(KEYS[key]))
                if ret == 0 then
                    return 0
                end
            end
            return 1
            """
        )

    async def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if not await self.contains(item):
            if not isinstance(item, str):
                item = str(item)
            offsets = list(map(lambda x: x.hash(item), self.hashmaps))
            await self._add_script(keys=[self.key] + offsets)
            self.count += 1
            return True
        return False

    async def clear(self) -> None:
        """清空过滤器"""
        await self.redis_client.delete(self.key)
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        raise NotImplementedError("use await self.contains() instead")

    async def contains(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        offsets = list(map(lambda x: x.hash(item), self.hashmaps))
        result = await self._contains_script(keys=[self.key] + offsets)
        return bool(result)


class ChunkedRedisBloomFilter(BaseBloomFilter):
    """BloomFilter that uses Redis, Chunk big keys"""

    def __init__(
        self,
        redis_client,
        key: str,
        capacity: int,
        error_rate: Optional[float] = 0.001,
        hash_type: Optional[Type[BaseHash]] = MMH3HashMap,
    ):
        """
        Redis简单存储 会拆分大Key
        :param key: redis中的键名
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
        # 按照上述算法，可见，这里限制最大分key数量为4096  K大说最好10000以下，除非有设置过期
        self._add_script = self.redis_client.register_script(
            """
            local redis_chunk_key = KEYS[1]
            for key = 2, #KEYS do
                redis.call("SETBIT", redis_chunk_key, tonumber(KEYS[key]), 1)
            end
            return {ok='OK'}
            """
        )
        self._contains_script = self.redis_client.register_script(
            """
           local redis_chunk_key = KEYS[1]
            for key = 2, #KEYS do
                local ret = redis.call("GETBIT", redis_chunk_key, tonumber(KEYS[key]))
                if ret == 0 then
                    return 0
                end
            end
            return 1
            """
        )

    async def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if not await self.contains(item):
            if not isinstance(item, str):
                item = str(item)
            redis_chunk_key = (
                self.key
                + ":"
                + str(
                    int(md5(item.encode()).hexdigest()[0 : self.value_split_num], 16)
                    % self.block_num
                )
            )  # 计算分片key的值 后缀是:0,1...
            offsets = list(map(lambda x: x.hash(item), self.hashmaps))
            await self._add_script(keys=[redis_chunk_key] + offsets)  # todo return?
            self.count += 1
            return True
        return False

    async def clear(self) -> None:
        """清空过滤器"""
        await self.redis_client.delete(
            *(
                self.key + ":" + str(i)
                for i in range(self.block_num if self.block_num <= 4096 else 4096)
            )
        )
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        raise NotImplementedError("use await self.contains() instead")

    async def contains(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        redis_chunk_key = (
            self.key
            + ":"
            + str(
                int(md5(item.encode()).hexdigest()[0 : self.value_split_num], 16)
                % self.block_num
            )
        )
        offsets = list(map(lambda x: x.hash(item), self.hashmaps))
        result = await self._contains_script(keys=[redis_chunk_key] + offsets)
        return bool(result)


class CountRedisBloomFilter(BaseBloomFilter):
    """
    BloomFilter that uses Redis, capable of remove elements
    使用hashmap来代替，避免产生大量key
    """

    def __init__(
        self,
        redis_client,
        key: str,
        capacity: int,
        error_rate: Optional[float] = 0.001,
        hash_type: Optional[Type[BaseHash]] = MMH3HashMap,
    ):
        """
        Redis key当做counter
        :param key: redis中的键名
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
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]  # k个hash函数

        self._add_script = self.redis_client.register_script(
            """
            if tonumber(#KEYS) < 2 then
                return { err = "wrong argument numbers" }
            end
            for key = 2, #KEYS do
                redis.call("HINCRBY", KEYS[1], KEYS[key], 1)
            end
            return { ok = "incr by field success" }
            """
        )
        self._remove_script = self.redis_client.register_script(
            """
            if tonumber(#KEYS) < 2 then
                return { err = "wrong argument numbers" }
            end

            for key = 2, #KEYS do
                redis.call("HINCRBY", KEYS[1], KEYS[key], -1)
            end
            return { ok = "decr by field success" }
            """
        )
        self._contains_script = self.redis_client.register_script(
            """
            if #KEYS < 2 then
                return { err = "wrong argument numbers" }
            end
            if redis.call("EXISTS", KEYS[1]) == 0 then
                return 0
            end
            for key = 2, #KEYS do
                local ret = redis.call("HGET", KEYS[1], KEYS[key])
                if not ret then
                    ret = 0
                else
                    ret = tonumber(ret)
                end
                if ret<=0 then
                    return 0
                end
            end
            return 1
            """
        )

    async def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if not await self.contains(item):
            if not isinstance(item, str):
                item = str(item)
            offsets = list(map(lambda x: x.hash(item), self.hashmaps))  # k个偏移量
            await self._add_script(keys=[self.key] + offsets)
            self.count += 1
            return True
        return False

    async def remove(self, item: Any) -> bool:
        """
        删除元素
        :param item:
        :return: 是否删除
        """
        if await self.contains(item):
            if not isinstance(item, str):
                item = str(item)
            offsets = list(map(lambda x: x.hash(item), self.hashmaps))
            await self._remove_script(keys=[self.key] + offsets)
            self.count -= 1
            return True
        return False

    async def clear(self) -> None:
        """清空过滤器"""
        await self.redis_client.delete(self.key)
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        raise NotImplementedError("use await self.contains() instead")

    async def contains(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)
        offsets = list(map(lambda x: x.hash(item), self.hashmaps))
        result = await self._contains_script(keys=[self.key] + offsets)
        return bool(result)

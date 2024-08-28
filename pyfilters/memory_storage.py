# -*- coding: utf-8 -*-
import array
from typing import Any, Optional, Type

import bitarray
from typing_extensions import Literal

from pyfilters.abc import BaseBloomFilter, BaseHash
from pyfilters.hashmap import MMH3HashMap
from pyfilters.utils import calculation_bloom_filter

_IntTypeCode = Literal["b", "B", "h", "H", "i", "I", "l", "L", "q", "Q"]


# https://github.com/Hexmagic/pybloom3/blob/master/pybloom/pybloom.py  slow implementation
# https://github.com/leffss/ScrapyRedisBloomFilterBlockCluster/blob/master/scrapy_redis_bloomfilter_block_cluster/
# good implementation


class MemoryBloomFilter(BaseBloomFilter):
    """BloomFilter that uses memory"""

    def __init__(
        self,
        capacity: int,
        error_rate: Optional[float] = 0.001,
        hash_type: Optional[Type[BaseHash]] = MMH3HashMap,
    ):
        """

        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        m, k, *_ = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m  # len of bitarray
        self.k = k  # number of hash functions
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]
        self.bitarray = bitarray.bitarray(m, endian="little")
        self.bitarray.setall(False)

    def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if item not in self:
            if not isinstance(item, str):
                item = str(item)

            for map_ in self.hashmaps:
                value = map_.hash(item)
                assert 0 <= value < self.m
                self.bitarray[value] = True
            self.count += 1
            return True
        return False

    def clear(self) -> None:
        """清空过滤器"""
        self.bitarray.setall(False)
        self.count = 0

    def __len__(self) -> int:
        return self.count

    def __contains__(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)

        def _m(x):
            value = x.hash(item)
            assert 0 <= value < self.m
            return self.bitarray[value]

        return all(map(_m, self.hashmaps))


class CountMemoryBloomFilter(BaseBloomFilter):
    """可以删除数据的过滤器 消耗大量内存"""

    def __init__(
        self,
        capacity: int,
        error_rate: Optional[float] = 0.001,
        hash_type: Optional[Type[BaseHash]] = MMH3HashMap,
        array_type: Optional[_IntTypeCode] = "L",
    ):
        """

        :param capacity: 容量
        :param error_rate: 错误率
        :param hash_type: hash函数类型
        :param array_type: array.array类型标志
        """
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")
        m, k, *_ = calculation_bloom_filter(capacity, error_rate)
        self.count = 0
        self.m = m  # len of array
        self.k = k  # number of hash functions
        self.seeds = self._seeds.copy()[0:k]
        self.hashmaps = [hash_type(m, seed) for seed in self.seeds]
        self.array = array.array(array_type, [0] * m)

    def add(self, item: Any) -> bool:
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        if item not in self:
            if not isinstance(item, str):
                item = str(item)

            for map_ in self.hashmaps:
                value = map_.hash(item)
                assert 0 <= value < self.m
                self.array[value] += 1
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

            for map_ in self.hashmaps:
                value = map_.hash(item)
                assert 0 <= value < self.m
                self.array[value] -= 1
            self.count -= 1
            return True
        return False

    def clear(self) -> None:
        """清空过滤器"""
        for i in range(len(self.array)):
            self.array[i] = 0
        self.count = 0

    def __contains__(self, item: Any) -> bool:
        if not isinstance(item, str):
            item = str(item)

        def _m(x):
            value = x.hash(item)
            assert 0 <= value < self.m
            return self.array[value] > 0

        return all(map(_m, self.hashmaps))

    def __len__(self) -> int:
        return self.count

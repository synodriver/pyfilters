# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import List

from _collections_abc import _check_methods


class BaseBloomFilter(ABC):
    """Base BloomFilter"""

    _seeds: List[int] = [
        543,
        460,
        171,
        876,
        796,
        607,
        650,
        81,
        837,
        545,
        591,
        946,
        846,
        521,
        913,
        636,
        878,
        735,
        414,
        372,
        344,
        324,
        223,
        180,
        327,
        891,
        798,
        933,
        493,
        293,
        836,
        10,
        6,
        544,
        924,
        849,
        438,
        41,
        862,
        648,
        338,
        465,
        562,
        693,
        979,
        52,
        763,
        103,
        387,
        374,
        349,
        94,
        384,
        680,
        574,
        480,
        307,
        580,
        71,
        535,
        300,
        53,
        481,
        519,
        644,
        219,
        686,
        236,
        424,
        326,
        244,
        212,
        909,
        202,
        951,
        56,
        812,
        901,
        926,
        250,
        507,
        739,
        371,
        63,
        584,
        154,
        7,
        284,
        617,
        332,
        472,
        140,
        605,
        262,
        355,
        526,
        647,
        923,
        199,
        518,
    ]

    @abstractmethod
    def add(self, item):
        """
        加入元素
        :param item: 一个可以变成str的对象
        :return: bool 是否插入成功
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self):
        """清空过滤器"""
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, item):
        raise NotImplementedError

    @abstractmethod
    def __len__(self):
        raise NotImplementedError


class BaseHash(ABC):
    """Base Hash Functions"""

    def __init__(self, m: int, seed: int):
        ...

    @abstractmethod
    def hash(self, value):
        raise NotImplementedError

    @classmethod
    def __subclasshook__(cls, subclass):
        return _check_methods(cls, "hash")

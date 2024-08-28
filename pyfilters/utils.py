# -*- coding: utf-8 -*-
import math
from typing import Tuple


def calculation_bloom_filter(n: int, p: float) -> Tuple[int, int, int, int]:
    """
    计算布隆过滤器的位数m hash函数个数k
    :param n: 插入的元素的个数
    :param p: 误报率
    :return: 布隆过滤器位数, hash函数个数 需要内存(Mb) 需要多少内存块
    """
    m = -(n * (math.log(p)) / (math.log(2)) ** 2)  # bit number bitarray长度
    k = m / n * math.log(2)  # hash functions
    mem = math.ceil(m / 8 / 1024 / 1024)  # 需要的多少 M 内存
    block_num = math.ceil(mem / 512)  # 需要多少个 Redis 512M 的内存块 Redis一个string最大512M
    return math.ceil(m), math.ceil(k), mem, block_num

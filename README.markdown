# 由python实现的一些列高效的过滤器算法实现

- 基于redis和memory
- 低时间复杂度

## Useage

```python
from pyfilters import MemoryBloomFilter

bf = MemoryBloomFilter(10000, 0.00001)
for i in range(1000):
    bf.add(i)
for i in range(1000):
    assert i in bf
assert 1001 not in bf
```

## Advanced usage


- 计数形布隆过滤器，可以删除数据

```python
from pyfilters import CountMemoryBloomFilter

cbf = CountMemoryBloomFilter(10000, 0.00001)
for i in range(1000):
    cbf.add(i)
for i in range(1000):
    assert i in cbf
cbf.remove(1)
assert 1 not in cbf
```

- redis分块布隆过滤器，避免单key过大

```python
from redis import Redis
from pyfilters import ChunkedRedisBloomFilter

bf = ChunkedRedisBloomFilter(Redis(), "test_bloomfilter", 10000, 0.00001)
for i in range(1000):
    bf.add(i)
for i in range(1000):
    assert i in bf
assert 1001 not in bf
```


- 分块计数形redis布隆过滤器,可以删除数据

```python
from redis import Redis
from pyfilters import CountRedisBloomFilter

rcbf = CountRedisBloomFilter(Redis(), "test_countbloomfilter", 10000, 0.00001)
for i in range(1000):
    rcbf.add(i)
for i in range(1000):
    assert i in rcbf
rcbf.remove(1)
assert 1 not in rcbf
```
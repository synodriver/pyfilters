import unittest

from pyfilters import MemoryBloomFilter, HashlibHashMap, CountMemoryBloomFilter


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.bf = MemoryBloomFilter(10000, 0.00001, HashlibHashMap)
        self.cbf = CountMemoryBloomFilter(10000, 0.00001, HashlibHashMap)

    def test_add(self):
        for i in range(1000):
            self.bf.add(i)
            self.cbf.add(i)
        for i in range(1000):
            self.assertTrue(i in self.bf, f"{i}居然不在里面")
            self.assertTrue(i in self.cbf, f"{i}居然不在里面")
        self.assertNotIn(1001, self.bf, "1001居然在里面了")
        self.assertNotIn(1001, self.cbf, "1001居然在里面了")

    def test_remove(self):
        self.cbf.remove(1)
        self.assertNotIn(1, self.cbf, "1居然没有被remove")

    def test_clear(self):
        self.bf.clear()
        self.assertNotIn(1, self.bf)
        self.cbf.clear()
        self.assertNotIn(1, self.cbf)


if __name__ == '__main__':
    unittest.main()

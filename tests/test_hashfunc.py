import unittest

from pyfilters import HashlibHashMap, MMH3HashMap, PyHashMap
from pyfilters.abc import BaseHash


class PurePyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.hashmap = PyHashMap(10000, 49)
        self.hashmap2 = MMH3HashMap(10000, 49)
        self.hashmap3 = HashlibHashMap(10000, 49)

    def test_purepy(self):
        for i in range(1000):
            v = self.hashmap.hash(str(i))
            print(f"hashing {i}")
            if v < 0:
                pass
            self.assertTrue(10000 > v >= 0)
        # v = self.hashmap.hash(str(312))

    def test_mmh3(self):
        for i in range(1000):
            v = self.hashmap2.hash(str(i))
            print(f"hashing {i}")
            if v < 0:
                pass
            self.assertTrue(10000 > v >= 0)

    def test_hashlib(self):
        for i in range(1000):
            v = self.hashmap3.hash(str(i))
            print(f"hashing {i}")
            if v < 0:
                pass
            self.assertTrue(10000 > v >= 0)

    def test_subclass(self):
        class A:
            def hash(self, v):
                return v

        self.assertTrue(isinstance(A(), BaseHash))


if __name__ == "__main__":
    unittest.main()

import unittest

from pyfilters import PyHashMap


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.hashmap = PyHashMap(10000, 49)

    def test_something(self):
        for i in range(1000):
            v = self.hashmap.hash(str(i))
            print(f"hashing {i}")
            self.assertTrue(10000 > v >= 0)
        # v = self.hashmap.hash(str(312))


if __name__ == '__main__':
    unittest.main()

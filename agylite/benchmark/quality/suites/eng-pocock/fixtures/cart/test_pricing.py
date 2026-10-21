import unittest

from cart.pricing import total


class TestTotal(unittest.TestCase):
    def test_no_discount(self):
        self.assertEqual(total([(500, 2), (250, 1)]), 1250)

    def test_ten_percent(self):
        self.assertEqual(total([(1000, 1)], 10), 900)


if __name__ == "__main__":
    unittest.main()

from PyQt5.Qt import QApplication
import sys
import unittest

from webola.grid import TeamButton


class Test(unittest.TestCase):

    def setUp(self):
        self.b = TeamButton(1)

    def check(self, a, b):
        self.b.name = a
        self.assertEqual(self.b.get_name(), b)

    def test_01(self): self.check('1234567890123456789',
                                  '1234567890123456789')
    def test_02(self): self.check('12345678901234567890',
                                  '12345678901234567890')
    def test_03(self): self.check('123456789012345678901',
                                  '12345678901234567...')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    unittest.main()


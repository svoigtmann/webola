from PyQt5.Qt import QApplication
import sys
import unittest

from webola.grid import ButtonGroup

class MockTeam():
    def __init__(self, n,r,s,t):
        self.nummer         = n
        self.running        = r
        self.schiessen      = s
        self.schiessen_time = t
        
class MockButton():
    def __init__(self, n,r,s,t):
        self.team = MockTeam(n,r,s,t)
        
class Test(unittest.TestCase):

    def check(self, a,b,c):
        self.assertEqual("".join(str(b.team.nummer) for b in ButtonGroup.sorted_buttons([MockButton(*a),
                                                                                         MockButton(*b)])), c)

    def test_01(self): self.check((1,0,0,0), (2,0,0,0), '12')
    def test_02(self): self.check((2,0,0,0), (1,0,0,0), '12')
    def test_03(self): self.check((1,1,0,0), (2,2,0,0), '21')
    def test_04(self): self.check((1,0,1,0), (2,0,2,0), '21')
    def test_05(self): self.check((1,0,1,2), (2,0,1,1), '21')
    def test_06(self): self.check((1,2,1,0), (2,2,0,0), '12')
    def test_07(self): self.check((1,2,1,0), (2,2,2,0), '21')
    def test_08(self): self.check((1,2,2,1), (2,2,2,0), '21')
    def test_09(self): self.check((2,2,0,1), (1,2,0,2), '21')
    def test_10(self): self.check((2,2,0,1), (1,2,0,1), '12')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    unittest.main()


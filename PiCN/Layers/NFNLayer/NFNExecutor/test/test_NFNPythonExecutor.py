"""Tests for the NFNPythonExecutor"""

import unittest

from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor

class test_NFNPythonExecutor(unittest.TestCase):
    """Tests for the NFNPythonExecutor"""

    def setUp(self):
        self.executor = NFNPythonExecutor()

    def tearDown(self):
        pass

    def test_single_simple_function_call(self):
        """Test a very simple function code with no Parameter"""
        NF = \
"""PYTHON
f
def f():
    return 3
"""
        res = self.executor.execute(NF, [])
        self.assertEqual(res, 3)

    def test_single_function_call(self):
        """Test a very simple function code with Parameter"""
        NF = \
"""PYTHON
f
def f(a, b):
    return a*b
"""

        res = self.executor.execute(NF, [2,3])
        self.assertEqual(res, 6)

    def test_single_function_call_library_function(self):
        """Test a very simple function code with library call"""
        NF = \
"""PYTHON
f
def f(a, b):
    return max(a,b)
"""
        res = self.executor.execute(NF, [2, 3])
        self.assertEqual(res, 3)

    def test_single_function_call_forbitten_library_function(self):
        """Test a very simple function code forbitten libary call"""
        NF = \
"""PYTHON
f
def f(a):
    return open(a)
"""
        res = self.executor.execute(NF, ["data.txt"])
        self.assertEqual(res, None)

    def test_multiple_function_call(self):
        """Test a very simple function code with second function"""
        NF = \
"""PYTHON
f
def g(b):
    return b*b
def f(a):
    return g(a*a)
"""
        res = self.executor.execute(NF, [2])
        self.assertEqual(res, 16)

    def test_multiple_function_call_libray_name(self):
        """Test a very simple function code second function with library name"""
        NF = \
"""PYTHON
f
def open(b):
    return 2
def f(a):
    return open(a)
"""
        res = self.executor.execute(NF, ['test.txt'])
        self.assertEqual(res, 2)

    def test_single_function_call(self):
        """Test a loop function code """
        NF = \
            """PYTHON
f
def f(a):
    res = 0
    for i in range(0,a):
        res = res + i
    return res
"""
        res = self.executor.execute(NF, [4])
        self.assertEqual(res, 6)

    def test_class(self):
        """Test with a class"""
        NF = \
        """PYTHON
        f
class TestClass(object):
    def __init___(self):
        self.a = 0
def f(a):
    res = 0
    x = TestClass()
    for i in range(0,a):
        res = res + i
    return res
    """
        res = self.executor.execute(NF, [4])
        self.assertEqual(res, None)
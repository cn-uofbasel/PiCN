"""Tests for the x86Executor"""

import unittest

from PiCN.Layers.NFNLayer.NFNExecutor import x86Executor

class test_NFNPythonExecutor(unittest.TestCase):
    """Tests for the NFNPythonExecutor"""

    def setUp(self):
        self.executor = x86Executor()
        nfnfile = open('NFN-x86-file', 'rb')
        self.content_obj = nfnfile.read()

    def tearDown(self):
        pass

    def test_get_entry_function_name(self):
        'test if entry funciton name is read correctly'
        res = self.executor._get_entry_function_name(self.content_obj)
        self.assertEqual('test', res[0])

    def test_execute_shared_lib(self):
        fname, fcode = self.executor._get_entry_function_name(self.content_obj)
        res = self.executor.execute(self.content_obj, ['hello'])
        self.assertEqual(5, res)

        res = self.executor.execute(self.content_obj, ['hello123'])
        self.assertEqual(8, res)

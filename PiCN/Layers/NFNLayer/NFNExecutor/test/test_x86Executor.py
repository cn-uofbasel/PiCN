"""Tests for the x86Executor"""

import os
import platform
import unittest

from PiCN.Layers.NFNLayer.NFNExecutor import x86Executor

class test_NFNPythonExecutor(unittest.TestCase):
    """Tests for the NFNPythonExecutor"""

    def setUp(self):
        self.executor = x86Executor()
        self.content_obj = None
        if platform.system() != 'Darwin':
            return
        # Fixture is CWD-relative (legacy nose chdir); skip when absent.
        if not os.path.isfile('NFN-x86-file-osx'):
            return
        with open('NFN-x86-file-osx', 'r') as nfnfile:
            self.content_obj = nfnfile.read()

    def tearDown(self):
        pass

    def _require_darwin_fixture(self):
        if platform.system() != 'Darwin':
            self.skipTest("Test only for OSX available")
        if self.content_obj is None:
            self.skipTest("NFN-x86-file-osx fixture not available")

    def test_get_entry_function_name(self):
        'test if entry funciton name is read correctly'
        self._require_darwin_fixture()
        res = self.executor._get_entry_function_name(self.content_obj)
        self.assertEqual('test', res[0])

    def test_execute_shared_lib(self):
        self._require_darwin_fixture()
        fname, fcode = self.executor._get_entry_function_name(self.content_obj)
        res = self.executor.execute(self.content_obj, ['hello'])
        self.assertEqual(5, res)

        res = self.executor.execute(self.content_obj, ['hello123'])
        self.assertEqual(8, res)

"""Test of in-memory Forwarding Information Base using longest prefix matching"""

import multiprocessing
import unittest

from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Packets import Name


class test_ForwardingInformationBaseMemoryPrefix(unittest.TestCase):
    """Test of in-memory Forwarding Information Base using longest prefix matching"""

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.fib = ForwardingInformationBaseMemoryPrefix()

    def tearDown(self):
        pass

    def test_add_entry_to_fib(self):
        """Test add entry to fib"""
        fid = 1
        name = Name("/test/data")
        self.fib.add_fib_entry(name, fid)
        entry = self.fib._container[0]
        self.assertEqual(entry.name, name)
        self.assertEqual(entry.faceid, fid)

    def test_find_entry_to_fib(self):
        """Test finding a fib entry"""
        fid = 1
        name = Name("/test/data")
        self.fib.add_fib_entry(name, fid)
        entry = self.fib._container[0]
        self.assertEqual(entry.name, name)
        self.assertEqual(entry.faceid, fid)
        fib_entry = self.fib.find_fib_entry(name)
        self.assertEqual(fib_entry.name, name)
        self.assertEqual(fib_entry.faceid, fid)

    def test_find_entry_to_fib_multiple_entries(self):
        """Test finding a fib entry with multiple entries"""
        fid1 = 1
        fid2 = 2
        name1 = Name("/test/data")
        name2 = Name("/data/test")
        self.fib.add_fib_entry(name2, fid2)
        self.fib.add_fib_entry(name1, fid1)
        entry = self.fib._container[1]
        self.assertEqual(entry.name, name2)
        self.assertEqual(entry.faceid, fid2)
        fib_entry = self.fib.find_fib_entry(name1)
        self.assertEqual(fib_entry.name, name1)
        self.assertEqual(fib_entry.faceid, fid1)

    def test_find_entry_to_fib_longest_match(self):
        """Test finding a fib using a longest match"""
        fid1 = 1
        fid2 = 2
        name1 = Name("/test/data")
        name2 = Name("/data")
        name3 = Name("/test/data/object")
        name4 = Name("/data/object/content")
        self.fib.add_fib_entry(name1, fid1)
        self.fib.add_fib_entry(name2, fid2)
        fib_entry1 = self.fib.find_fib_entry(name3)
        fib_entry2 = self.fib.find_fib_entry(name4)
        self.assertEqual(fib_entry1.name, name1)
        self.assertEqual(fib_entry2.name, name2)
        self.assertEqual(fib_entry1.faceid, fid1)
        self.assertEqual(fib_entry2.faceid, fid2)

    def test_find_entry_to_fib_no_match(self):
        """Test finding a fib entry with no match"""
        fid = 1
        name1 = Name("/test/data")
        name2 = Name("/data/test")
        self.fib.add_fib_entry(name1, fid)
        entry = self.fib._container[0]
        self.assertEqual(entry.name, name1)
        self.assertEqual(entry.faceid, fid)
        fib_entry = self.fib.find_fib_entry(name2)
        self.assertEqual(fib_entry, None)

    def test_remove_entry_to_fib(self):
        """Test remove a fib entry"""
        fid = 1
        name = Name("/test/data")
        self.fib.add_fib_entry(name, fid)
        entry = self.fib._container[0]
        self.assertEqual(entry.name, name)
        self.assertEqual(entry.faceid, fid)
        self.fib.remove_fib_entry(name)

    def test_get_already_used_fib_entry(self):
        """Test to get a fib entry if there are alreay used entries"""
        fid1 = 1
        fid2 = 2
        fid3 = 3
        n1 = Name("/test/data/content")
        n2 = Name("/test")
        n3 = Name("/test/data")
        already_used = []
        self.fib.add_fib_entry(n1, fid1)
        self.fib.add_fib_entry(n2, fid2)
        self.fib.add_fib_entry(n3, fid3)
        iname = Name("/test/data/content/object1")
        #test best match
        fib_entry = self.fib.find_fib_entry(iname)
        self.assertEqual(fib_entry.faceid, fid1)
        already_used.append(fib_entry)
        # test 2nd best match
        fib_entry = self.fib.find_fib_entry(iname, already_used)
        self.assertEqual(fib_entry.faceid, fid3)
        already_used.append(fib_entry)
        # test 3rd best match
        fib_entry = self.fib.find_fib_entry(iname, already_used)
        self.assertEqual(fib_entry.faceid, fid2)
        already_used.append(fib_entry)
        # test no match anymore best match
        fib_entry = self.fib.find_fib_entry(iname, already_used)
        self.assertEqual(fib_entry, None)

    def test_clear(self):
        self.fib.add_fib_entry(Name('/test/foo'), 42, static=True)
        self.fib.add_fib_entry(Name('/test/bar'), 1337, static=False)
        self.assertEqual(2, len(self.fib.container))
        self.fib.clear()
        self.assertEqual(1, len(self.fib.container))
        self.assertIsNotNone(self.fib.find_fib_entry(Name('/test/foo')))

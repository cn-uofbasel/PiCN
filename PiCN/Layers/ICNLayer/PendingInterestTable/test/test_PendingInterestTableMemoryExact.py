"""Tests for the in Memory Content Store with exact matching"""

import multiprocessing
import unittest

from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry
from PiCN.Layers.ICNLayer.PendingInterestTable.PendingInterestTableMemoryExact import PendingInterstTableMemoryExact
from PiCN.Packets import Name


class test_PendingInterstTableMemoryExact(unittest.TestCase):
    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.pit: PendingInterstTableMemoryExact = PendingInterstTableMemoryExact()

    def tearDown(self):
        pass

    def test_add_data_to_pit(self):
        """Test adding data to PIT"""
        fid = 1
        name = Name("/test/data")
        self.pit.add_pit_entry(name, fid)
        data = self.pit._container[0]
        self.assertEqual(data.name, name)

    def test_find_data_in_pit(self):
        """Test finding data in PIT exact"""
        fid = 1
        name = Name("/test/data")
        self.pit.add_pit_entry(name, fid)
        data = self.pit._container[0]
        self.assertEqual(data.name, name)
        res = self.pit.find_pit_entry(name)
        self.assertEqual(res.name, name)
        self.assertEqual(res.face_id, [fid])

    def test_find_data_in_pit_no_match(self):
        """Test finding data in PIT exact, with no match"""
        fid = 1
        name1 = Name("/test/data")
        name2 = Name("/data/test")
        self.pit.add_pit_entry(name1, fid)
        data = self.pit._container[0]
        self.assertEqual(data.name, name1)
        res = self.pit.find_pit_entry(name2)
        self.assertEqual(res, None)

    def test_find_data_to_pit_deduplication(self):
        """Test finding data in PIT with multiple fids"""
        fid1 = 1
        fid2 = 2

        name = Name("/test/data")
        self.pit.add_pit_entry(name, fid1)
        self.pit.add_pit_entry(name, fid2)
        data = self.pit._container[0]
        self.assertEqual(data.name, name)
        res = self.pit.find_pit_entry(name)
        self.assertEqual(res.name, name)
        self.assertEqual(res.face_id, [fid1, fid2])

    def test_find_data_to_pit_deduplication_samefid(self):
        """Test finding data in PIT with two time same fids"""
        fid = 1
        name = Name("/test/data")
        self.pit.add_pit_entry(name, fid)
        self.pit.add_pit_entry(name, fid)
        data = self.pit._container[0]
        self.assertEqual(data.name, name)
        res = self.pit.find_pit_entry(name)
        self.assertEqual(res.name, name)
        self.assertEqual(res.face_id, [fid])

    def test_remove_data_from_pit(self):
        """Test removing data from PIT"""
        fid = 1
        name = Name("/test/data")
        self.pit.add_pit_entry(name, fid)

        data = self.pit._container[0]
        self.assertEqual(data.name, name)
        self.assertEqual(len(self.pit._container), 1)
        self.pit.remove_pit_entry(name)
        self.assertEqual(len(self.pit._container), 0)

    def test_add_already_used_fib_entry(self):
        """Test adding an already used FIB Entry"""
        n1 = Name("/test/data")
        fib_entry = ForwardingInformationBaseEntry(n1, 2, False)
        self.pit.add_pit_entry(n1, 1, None, False)
        self.pit.add_used_fib_entry(n1, fib_entry)
        self.assertEqual(self.pit.get_already_used_pit_entries(n1)[0], fib_entry)

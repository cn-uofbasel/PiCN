"""Tests for the Thunk List"""

import unittest

from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Packets import Name

class test_ThunkList(unittest.TestCase):

    def setUp(self):
        self.thunklist = ThunkList()

    def tearDown(self):
        pass

    def test_add_entry_to_thunk_table(self):
        """Test adding an entry to the thunk table"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        self.assertEqual(len(self.thunklist.container), 1)
        self.assertEqual(self.thunklist.container[0].name, name)
        self.assertEqual(self.thunklist.container[0].id, id)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[0]), None)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[1]), None)

    def test_get_entry_from_thunklist(self):
        """Test get entry from name and id"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        entry_name = self.thunklist.get_entry_from_name(name)
        entry_id = self.thunklist.get_entry_from_id(id)
        self.assertEqual(entry_name, entry_id)
        self.assertEqual(entry_name.name, name)
        self.assertEqual(entry_id.id, id)

    def test_add_awaiting_data(self):
        """Test add awaiting data to entry"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        self.thunklist.add_awaiting_data(name, Name("/test/data/d3"))
        self.assertEqual(len(self.thunklist.container[0].awaiting_data), 3)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(Name("/test/data/d3")), None)

    def test_add_estimated_cost_to_awaiting_data(self):
        """Test adding cost to awaiting data"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        self.thunklist.add_estimated_cost_to_awaiting_data(awaiting_data[1], 5)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[0]), None)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[1]), 5)
        self.thunklist.add_estimated_cost_to_awaiting_data(awaiting_data[1], 3)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[0]), None)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[1]), 3)
        self.thunklist.add_estimated_cost_to_awaiting_data(awaiting_data[1], 4)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[0]), None)
        self.assertEqual(self.thunklist.container[0].awaiting_data.get(awaiting_data[1]), 3)

    def test_remove_awaiting_data(self):
        """Test remove awaiting data from the list"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        self.thunklist.remove_awaiting_data(awaiting_data[0])
        self.assertEqual(len(self.thunklist.container), 1)
        self.assertEqual(list(self.thunklist.container[0].awaiting_data.keys())[0], awaiting_data[1])

    def test_remove_entry(self):
        """Test remove entry"""
        name = Name("/test/data")
        id = 2
        awaiting_data = [Name("/test/data/d1"), Name("/test/data/d2")]
        self.thunklist.add_entry_to_thunk_table(name, id, awaiting_data)
        self.thunklist.remove_entry_from_thunk_table(name)
        self.assertEqual(len(self.thunklist.container), 0)

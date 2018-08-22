import unittest

from PiCN.Layers.TimeoutPreventionLayer import TimeoutPreventionMessageDict
from PiCN.Packets import Name

class test_TimeoutPreventionMessageDict(unittest.TestCase):

    def setUp(self):
        self.dict = TimeoutPreventionMessageDict()

    def tearDown(self):
        pass

    def test_add_entry_to_timeout_prevention_dict(self):
        name = Name("/test/data")
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(1)
        self.dict.add_entry(name, entry)
        self.assertTrue(name in self.dict.container)

    def test_create_entry_in_timeout_prevention_dict(self):
        name = Name("/test/data")
        self.dict.create_entry(name, 1)
        self.assertTrue(name in self.dict.container)

    def test_get_entry_from_timeout_prevention_dict(self):
        name = Name("/test/data")
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(1)
        self.dict.add_entry(name, entry)
        self.assertTrue(name in self.dict.container)
        entry2 = self.dict.get_entry(name)
        self.assertEqual(entry, entry2)

    def test_remove_entry_from_timeout_prevention_dict(self):
        name = Name("/test/data")
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(1)
        self.dict.add_entry(name, entry)
        self.dict.remove_entry(name)
        self.assertFalse(name in self.dict.container)

    def test_update_timestamp_in_timeout_prevention_dict(self):
        name = Name("/test/data")
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(1)
        ts1 = entry.timestamp
        self.dict.add_entry(name, entry)
        self.dict.update_timestamp(name)
        self.assertTrue(ts1 < self.dict.get_entry(name).timestamp)
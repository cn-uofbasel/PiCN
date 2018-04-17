"""Test the NFNComputationList"""

import unittest

from PiCN.Packets import Name, Content
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationTableEntry

class test_NFNComputationList(unittest.TestCase):

    def setUp(self):
        self.computationList: NFNComputationList = NFNComputationList()

    def tearDown(self):
        pass

    def test_add_computation(self):
        """Test adding a computation to the List"""
        name = Name("/test")
        self.computationList.add_computation(name)
        self.assertTrue(NFNComputationTableEntry(name) in self.computationList.container)

        name1 = Name("/test")
        self.computationList.add_computation(name1)
        self.assertTrue(NFNComputationTableEntry(name1) in self.computationList.container)
        self.assertEqual(len(self.computationList.container), 1)

        name2 = Name("/data")
        self.computationList.add_computation(name2)
        self.assertTrue(NFNComputationTableEntry(name) in self.computationList.container)
        self.assertTrue(NFNComputationTableEntry(name2) in self.computationList.container)
        self.assertEqual(len(self.computationList.container), 2)

    def test_push_data(self):
        """Test the function push data"""
        name = Name("/test")
        name1 = Name("/data")
        self.computationList.add_computation(name)
        self.computationList.container[0].awaiting_data.append(name1)
        self.computationList.push_data(Content(name1))
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 0)

    def test_ready_computations(self):
        """Test if the list of ready computations is complete"""
        name = Name("/test")
        name1 = Name("/data")
        name2 = Name("/hello")
        name3 = Name("/world")
        self.computationList.add_computation(name)
        self.computationList.add_computation(name1)
        self.computationList.add_computation(name2)
        self.computationList.add_computation(name3)
        request_name = Name("/request")
        request_name2 = Name("/request2")
        self.computationList.container[0].awaiting_data.append(request_name)
        self.computationList.container[1].awaiting_data.append(request_name)
        self.computationList.container[2].awaiting_data.append(request_name)
        self.computationList.container[3].awaiting_data.append(request_name2)
        self.computationList.push_data(Content(request_name))

        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(len(ready_comps), 3)
        self.assertEqual(ready_comps, self.computationList.container[:3])

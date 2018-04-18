"""Test the NFNComputationList"""

import time
import unittest

from PiCN.Packets import Name, Content
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationTableEntry
from PiCN.Layers.NFNLayer.R2C import SimpleR2CClient

class test_NFNComputationList(unittest.TestCase):

    def setUp(self):
        self.r2cclient = SimpleR2CClient()
        self.computationList: NFNComputationList = NFNComputationList(self.r2cclient)

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
        self.computationList.container[0].add_name_to_await_list(name1)
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
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.computationList.container[1].add_name_to_await_list(request_name)
        self.computationList.container[2].add_name_to_await_list(request_name)
        self.computationList.container[3].add_name_to_await_list(request_name2)
        self.computationList.push_data(Content(request_name))

        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(len(ready_comps), 3)
        self.assertEqual(ready_comps, self.computationList.container[:3])

    def test_ready_computations_excludes_r2c(self):
        """Test if the list of ready computations excludes R2C"""
        name = Name("/test/NFN")
        request_name = Name("/test/R2C")
        self.computationList.add_computation(name)
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(ready_comps, [NFNComputationTableEntry(name)])

    def test_computation_table_entry_ageing_no_nfn(self):
        """test the ageing of await list with non nfn entries"""
        name = Name("/test")
        request_name = Name("/request")
        self.computationList.add_computation(name)
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, []) #nothing to do, ageing returns empty list
        #wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        self.assertIsNone(res) #computation requirements could not be resolved, ageging returns None

    def test_computation_table_entry_ageing_nfn_single_awaits(self):
        """test the ageing of await list with nfn entries"""
        name = Name("/test/NFN")
        request_name = Name("/request/NFN")
        self.computationList.add_computation(name)
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, []) #nothing to do, ageing returns empty list
        #wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, [request_name]) # ageing returns list of names, for which timeout prevention is required

    def test_computation_table_entry_ageing_nfn_multiple_awaits(self):
        """test the ageing of await list with nfn entries"""
        name = Name("/test/NFN")
        request_name = Name("/request/NFN")
        request_name2 = Name("/request2/NFN")
        self.computationList.add_computation(name)
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.computationList.container[0].add_name_to_await_list(request_name2)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 2)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, []) #nothing to do, ageing returns empty list
        #wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, [request_name, request_name2]) # ageing returns list of names, for which timeout prevention is required
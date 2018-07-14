"""Test the NFNComputationList"""

import time
import unittest

from PiCN.Packets import Name, Content, Interest
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationState
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationTableEntry
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNAwaitListEntry
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser


class test_NFNComputationList(unittest.TestCase):
    def setUp(self):
        self.r2cclient = TimeoutR2CHandler()
        self.computationList: NFNComputationList = NFNComputationList(self.r2cclient, DefaultNFNParser())

    def tearDown(self):
        pass

    def test_add_computation(self):
        """Test adding a computation to the List"""
        name = Name("/test")
        self.computationList.add_computation(name, 0, Interest(name))
        self.assertTrue(NFNComputationTableEntry(name) in self.computationList.container)

        name1 = Name("/test")
        self.computationList.add_computation(name1, 0, Interest(name1))
        self.assertTrue(NFNComputationTableEntry(name1) in self.computationList.container)
        self.assertEqual(len(self.computationList.container), 1)

        name2 = Name("/data")
        self.computationList.add_computation(name2, 0, Interest(name2))
        self.assertTrue(NFNComputationTableEntry(name) in self.computationList.container)
        self.assertTrue(NFNComputationTableEntry(name2) in self.computationList.container)
        self.assertEqual(len(self.computationList.container), 2)

    def test_get_computation(self):
        """Test getting an entry from the computation container"""
        name = Name("/test")
        self.computationList.add_computation(name, 0, Interest(name))
        get_name1 = Name("/test")
        res = self.computationList.get_computation(get_name1)
        self.assertEqual(res.original_name, name)

        get_name2 = Name("/data")
        res = self.computationList.get_computation(get_name2)
        self.assertIsNone(res)

    def test_remove_computation(self):
        """Test removing a computation from the container"""
        name = Name("/test")
        name2 = Name("/data")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 1, Interest(name2))

        self.assertEqual(len(self.computationList.container), 2)
        self.computationList.remove_computation(Name("/test"))
        self.assertEqual(len(self.computationList.container), 1)
        self.assertEqual(self.computationList.container[0].original_name, name2)

    def test_append_computation(self):
        """Test appending a computation"""
        name = Name("/test")
        name2 = Name("/data")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 1, Interest(name2))
        self.assertEqual(len(self.computationList.container), 2)
        comp = self.computationList.get_computation(name)
        self.computationList.remove_computation(name)
        self.assertEqual(len(self.computationList.container), 1)
        self.computationList.append_computation(comp)
        self.assertEqual(len(self.computationList.container), 2)
        self.assertEqual(self.computationList.container[0].original_name, name2)
        self.assertEqual(self.computationList.container[1].original_name, name)

    def test_update_status(self):
        """Test updating the status of a computation"""
        name = Name("/test")
        name2 = Name("/data")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 1, Interest(name2))
        self.assertEqual(self.computationList.container[0].comp_state, NFNComputationState.START)
        self.assertEqual(self.computationList.container[1].comp_state, NFNComputationState.START)
        self.computationList.update_status(name, NFNComputationState.FWD)
        self.assertEqual(self.computationList.get_computation(name).comp_state, NFNComputationState.FWD)
        self.assertEqual(self.computationList.get_computation(name2).comp_state, NFNComputationState.START)

    def test_add_to_await_list(self):
        """test adding data to the await list"""
        name = Name("/test")
        name2 = Name("/data")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 0, Interest(name2))
        self.computationList.add_awaiting_data(name, Name("/request"))
        self.assertEqual(self.computationList.get_computation(name).awaiting_data, [Name("/request")])
        self.assertEqual(self.computationList.get_computation(name2).awaiting_data, [])

    def test_push_data(self):
        """Test the function push data"""
        name = Name("/test")
        name1 = Name("/data")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.container[0].add_name_to_await_list(name1)
        self.computationList.push_data(Content(name1))
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 0)

    def test_ready_computations(self):
        """Test if the list of ready computations is complete"""
        name = Name("/test")
        name1 = Name("/data")
        name2 = Name("/hello")
        name3 = Name("/world")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name1, 1, Interest(name1))
        self.computationList.add_computation(name2, 2, Interest(name2))
        self.computationList.add_computation(name3, 3, Interest(name3))
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
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(ready_comps, [NFNComputationTableEntry(name)])

    def test_computation_table_entry_ageing_no_nfn(self):
        """test the ageing of await list with non nfn entries"""
        name = Name("/test")
        request_name = Name("/request")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, [])  # nothing to do, ageing returns empty list
        # wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        self.assertIsNone(res)  # computation requirements could not be resolved, ageging returns None

    def test_computation_table_entry_ageing_nfn_single_awaits(self):
        """test the ageing of await list with nfn entries"""
        name = Name("/test/NFN")
        request_name = Name("/request/NFN")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 1)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, [])  # nothing to do, ageing returns empty list
        # wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        compare_name = self.r2cclient.R2C_create_message(request_name)
        self.assertEqual(res, [request_name,
                               compare_name])  # ageing returns list of names, for which timeout prevention is required

    def test_computation_table_entry_ageing_nfn_multiple_awaits(self):
        """test the ageing of await list with nfn entries"""
        name = Name("/test/NFN")
        request_name = Name("/request/NFN")
        request_name2 = Name("/request2/NFN")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.container[0].timeout = 1
        self.computationList.container[0].add_name_to_await_list(request_name)
        self.computationList.container[0].add_name_to_await_list(request_name2)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 2)
        res = self.computationList.container[0].ageing()
        self.assertEqual(res, [])  # nothing to do, ageing returns empty list
        # wait for entry to timeout
        time.sleep(2)
        res = self.computationList.container[0].ageing()
        compare_name = self.r2cclient.R2C_create_message(request_name)
        compare_name2 = self.r2cclient.R2C_create_message(request_name2)
        self.assertEqual(res, [request_name, request_name2, compare_name,
                               compare_name2])  # ageing returns list of names, for which timeout prevention is required

    def test_computation_table_ageing_nfn_requests_and_ready_computations(self):
        """test the ageing of the computation table using nfn requests and check ready computations"""
        name = Name("/test/NFN")
        name2 = Name("/data/NFN")

        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 0, Interest(name2))

        self.computationList.container[0].timeout = 1.0
        self.computationList.container[1].timeout = 1.0

        request_name = Name("/request/NFN")
        request_name1 = Name("/request1/NFN")
        request_name2 = Name("/request2/NFN")

        self.computationList.container[0].add_name_to_await_list(request_name)
        self.computationList.container[0].add_name_to_await_list(request_name1)
        self.computationList.container[1].add_name_to_await_list(request_name2)

        self.assertEqual(len(self.computationList.container), 2)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 2)
        self.assertEqual(len(self.computationList.container[1].awaiting_data), 1)

        res = self.computationList.ageing()
        self.assertEqual(res, ([], []))
        time.sleep(2)

        res = self.computationList.ageing()

        self.assertEqual(len(self.computationList.container), 2)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 4)  # four since r2c
        self.assertEqual(len(self.computationList.container[1].awaiting_data), 2)  # two since r2c

        self.assertEqual(self.computationList.container[0].awaiting_data, [NFNAwaitListEntry(request_name),
                                                                           NFNAwaitListEntry(request_name1),
                                                                           NFNAwaitListEntry(
                                                                               self.r2cclient.R2C_create_message(
                                                                                   request_name)),
                                                                           NFNAwaitListEntry(
                                                                               self.r2cclient.R2C_create_message(
                                                                                   request_name1))
                                                                           ])

        self.assertEqual(res, ([request_name, request_name1,
                                self.r2cclient.R2C_create_message(request_name),
                                self.r2cclient.R2C_create_message(request_name1),
                                request_name2, self.r2cclient.R2C_create_message(request_name2)], []))

        self.computationList.push_data(Content(request_name))
        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(ready_comps, [])

        v = self.computationList.push_data(Content(request_name1))
        self.assertTrue(v)
        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(len(ready_comps), 1)
        self.assertEqual(ready_comps[0].original_name, name)

    def test_computation_table_ageing_mixed_requests_and_ready_computations(self):
        """test the ageing of the computation table using nfn and non nfn requests, and check ready computations"""
        name = Name("/test/NFN")
        name2 = Name("/data/NFN")

        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.add_computation(name2, 0, Interest(name2))

        self.computationList.container[0].timeout = 1.0
        self.computationList.container[1].timeout = 1.0

        request_name = Name("/request/NFN")
        request_name1 = Name("/request1")
        request_name2 = Name("/request2/NFN")

        self.computationList.container[0].add_name_to_await_list(request_name)
        self.computationList.container[0].add_name_to_await_list(request_name1)
        self.computationList.container[1].add_name_to_await_list(request_name2)

        self.assertEqual(len(self.computationList.container), 2)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 2)
        self.assertEqual(len(self.computationList.container[1].awaiting_data), 1)

        res = self.computationList.ageing()
        self.assertEqual(res, ([], []))
        time.sleep(2)

        res = self.computationList.ageing()

        self.assertEqual(len(self.computationList.container), 1)
        self.assertEqual(len(self.computationList.container[0].awaiting_data), 2)  # is two since it contains R2C

        self.assertEqual(res, ([request_name2, self.r2cclient.R2C_create_message(request_name2)], [name]))

        v = self.computationList.push_data(Content(request_name2))
        self.assertTrue(v)
        ready_comps = self.computationList.get_ready_computations()
        self.assertEqual(len(ready_comps), 1)
        self.assertEqual(ready_comps[0].original_name, name2)

    def test_computation_table_push_back(self):
        """Test the return value of the push back function"""
        name = Name("/test/NFN")
        self.computationList.add_computation(name, 0, Interest(name))
        reqeuest_name = Name("/request/name")
        v = self.computationList.push_data(Content(reqeuest_name))
        self.assertFalse(v)
        self.computationList.container[0].add_name_to_await_list(reqeuest_name)
        v = self.computationList.push_data(Content(reqeuest_name))
        self.assertTrue(v)

    def test_computation_table_rewrite(self):
        """test computation rewriting"""
        name = Name("/test/NFN")
        self.computationList.add_computation(name, 0, Interest(name))
        self.computationList.update_status(name, NFNComputationState.REWRITE)
        rewrite_list = [Name("/test1/NFN"), Name("/test2/NFN")]
        entry = self.computationList.get_computation(name)
        self.computationList.remove_computation(name)
        entry.rewrite_list = rewrite_list
        self.computationList.append_computation(entry)
        # do not match wrong data
        self.computationList.push_data(Content(Name("/test2/NFN")))
        self.assertEqual(self.computationList.get_computation(name).comp_state, NFNComputationState.REWRITE)
        # match correct data
        self.computationList.push_data(Content(Name("/test1/NFN"), "HelloWorld"))
        self.assertEqual(self.computationList.get_computation(name).comp_state, NFNComputationState.WRITEBACK)
        # test ready
        ready = self.computationList.get_ready_computations()
        self.assertEqual(name, ready[0].original_name)
        self.assertEqual("HelloWorld", ready[0].available_data.get(rewrite_list[0]))

    def test_r2c_timeout_prevention(self):  # todo same for rewrite
        """test r2c timeout prevention"""
        name1 = Name("/test1/NFN")
        name2 = Name("/test2/NFN")
        self.computationList.add_computation(name1, 0, Interest(name1))
        self.computationList.add_computation(name2, 0, Interest(name2))

        requestname1 = Name("/request1/NFN")
        requestname2 = Name("/request2/NFN")

        self.computationList.add_awaiting_data(name1, requestname1)
        self.computationList.add_awaiting_data(name2, requestname2)

        entry1 = self.computationList.get_computation(name1)
        self.computationList.remove_computation(name1)
        entry1.timeout = 1
        self.computationList.append_computation(entry1)

        entry2 = self.computationList.get_computation(name2)
        self.computationList.remove_computation(name2)
        entry2.timeout = 1
        self.computationList.append_computation(entry2)
        # ask for requests
        time.sleep(1)
        request_list = self.computationList.ageing()
        self.assertEqual(request_list, ([requestname1, self.r2cclient.R2C_create_message(requestname1),
                                         requestname2, self.r2cclient.R2C_create_message(requestname2)], []))

        self.computationList.push_data(Content(self.r2cclient.R2C_create_message(requestname1)))
        time.sleep(1)
        request_list = self.computationList.ageing()

        self.assertEqual(request_list, ([requestname1, self.r2cclient.R2C_create_message(requestname1)],
                                        [name2]))

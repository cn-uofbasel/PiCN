"""Tests for the BasicThunkLayer"""

import multiprocessing
import unittest

from PiCN.Layers.ThunkLayer import BasicThunkLayer
from PiCN.Packets import Name
from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory

class test_BasicThunkLayer(unittest.TestCase):
    """Tests for the BasicThunkLayer"""

    def setUp(self):
        factory = PiCNSyncDataStructFactory()

        factory.register("cs", ContentStoreMemoryExact)
        factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        factory.register("pit", PendingInterstTableMemoryExact)
        factory.register("faceidtable", FaceIDDict)
        factory.register("thunkTable", ThunkList)
        factory.register("planTable", PlanTable)
        factory.create_manager()

        self.cs = factory.manager.cs()
        self.fib = factory.manager.fib()
        self.pit = factory.manager.pit()
        self.faceidtable = factory.manager.faceidtable()
        self.thunkTable = factory.manager.thunkTable()
        self.planTable = factory.manager.planTable()

        self.parser = DefaultNFNParser()

        self.thunklayer = BasicThunkLayer(self.cs, self.fib, self.pit, self.faceidtable, self.thunkTable, self.planTable, self.parser)
        self.thunklayer.queue_to_higher = multiprocessing.Queue()
        self.thunklayer.queue_to_lower = multiprocessing.Queue()
        self.thunklayer.queue_from_higher = multiprocessing.Queue()
        self.thunklayer.queue_from_lower = multiprocessing.Queue()

        self.thunklayer.start_process()

    def tearDown(self):
        self.thunklayer.stop_process()

    def test_remove_thunk_marker(self):
        """Test if the system removes the thunk marker correctly"""
        name = Name("/test/data/THUNK/NFN")
        ret = self.thunklayer.removeThunkMarker(name)
        self.assertEqual(ret, Name("/test/data/NFN"))
        self.assertEqual(name, Name("/test/data/THUNK/NFN"))

        name2 = Name("/test/data/NFN")
        ret = self.thunklayer.removeThunkMarker(name2)
        self.assertEqual(ret, name2)
        self.assertEqual(ret, Name("/test/data/NFN"))

    def test_add_thunk_marker(self):
        """Test if system adds the thunk marker correctly"""
        name = Name("/test/data/NFN")
        ret = self.thunklayer.addThunkMarker(name)
        self.assertEqual(name, Name("/test/data/NFN"))
        self.assertEqual(ret, Name("/test/data/THUNK/NFN"))

        name2 = Name("/test/data/THUNK/NFN")
        ret = self.thunklayer.addThunkMarker(name2)
        self.assertEqual(ret, name2)
        self.assertEqual(ret, Name("/test/data/THUNK/NFN"))

    def test_generating_possible_names(self):
        """Test if the possible thunk names are generated correctly"""

        self.fib.add_fib_entry(Name("/func/f1"), [1])
        self.fib.add_fib_entry(Name("/func/f2"), [2])
        self.fib.add_fib_entry(Name("/test/data"), [4])

        comp_str = "/func/f1(/func/f2(/test/data/d1),/func/f3(/test/data/d2))"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)

        compare_list = ['/func/f1', '/func/f1(/func/f2(%/test/data/d1%),/func/f3(/test/data/d2))',
                        '/func/f1(/func/f2(/test/data/d1),/func/f3(%/test/data/d2%))', '%/func/f1%(/func/f2(/test/data/d1),'
                        '/func/f3(/test/data/d2))', '/func/f1(%/func/f2%(/test/data/d1),/func/f3(/test/data/d2))', '/func/f2',
                        '/func/f2(%/test/data/d1%)', '%/func/f2%(/test/data/d1)', '/test/data/d1', '/func/f3(%/test/data/d2%)',
                        '/test/data/d2']

        #self.assertEqual(len(name_list), len(compare_list))
        self.assertEqual(name_list, compare_list)



    def test_if_data_available_when_name_not_in_list(self):
        """Test if all_data_available returns None if name does not exist"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])

        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"

        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)

        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        res = self.thunklayer.all_data_available(Name("/test/data2"))
        self.assertIsNone(res)

    def test_if_data_available_when_one_data_available_not_all(self):
        """Test if all_data_available returns False if not all data cost are available"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])

        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"

        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)

        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 3)

        res = self.thunklayer.all_data_available(name)
        self.assertFalse(res)

    def test_if_data_available_when_one_data_available_not_all(self):
        """Test if all_data_available returns False if no data cost are available"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])

        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"

        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)

        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        res = self.thunklayer.all_data_available(name)
        self.assertFalse(res)


    def test_data_available_when_all_available(self):
        """Test if all_data_available returns None if name does not exist"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])

        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"

        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)

        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        for n in name_list:
            self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(n, 3)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

    def test_computing_cost_and_requests_simple1(self):
        """Test if the cheapest cost and requests are computed correctly for a simple computation"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])
        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)
        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[0], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 20)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[2], 30)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[3], 40)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

        res = self.thunklayer.compute_cost_and_requests(ast, self.thunklayer.active_thunk_table.get_entry_from_name(name))
        self.assertEqual(res, (20, '/fct/f1(%/dat/data/d1%)'))

    def test_computing_cost_and_requests_simple2(self):
        """Test if the cheapest cost and requests are computed correctly for a simple computation"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])
        comp_str = "/fct/f1(/dat/data/d1)"
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "NFN"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)
        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[0], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 20)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[2], 30)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[3], 5)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

        res = self.thunklayer.compute_cost_and_requests(ast, self.thunklayer.active_thunk_table.get_entry_from_name(name))
        self.assertEqual(res, (15, ['/dat/data/d1', '/fct/f1']))

    def test_computing_cost_and_requests_simple3(self):
        """Test if the cheapest cost and requests are computed correctly for a simple computation"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])
        comp_str = '/fct/f1(/dat/data/d1,"Hello World")'
        name = Name("/fct/f1")
        name += '_(/dat/data/d1,"Hello World")'
        name += "NFN"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)
        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[0], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 20)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[2], 30)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[3], 5)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

        res = self.thunklayer.compute_cost_and_requests(ast, self.thunklayer.active_thunk_table.get_entry_from_name(name))
        self.assertEqual(res, (15, ['/dat/data/d1', '/fct/f1']))

    def test_computing_cost_and_requests1(self):
        """Test if the cheapest cost and requests are computed correctly for a computation"""
        self.fib.add_fib_entry(Name("/fct"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])
        comp_str = '/fct/f1(/dat/data/d1,"Hello World",/fct/f2(/dat/d2))'
        name = Name("/fct/f1")
        name += '_(/dat/data/d1,"Hello World",/fct/f2(/dat/d2))'
        name += "NFN"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)
        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[0], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[2], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[3], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[4], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[5], 20)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[6], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[7], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[8], 25)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[9], 5)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

        res = self.thunklayer.compute_cost_and_requests(ast, self.thunklayer.active_thunk_table.get_entry_from_name(name))
        self.assertEqual(res, (40, ['/dat/data/d1', '/fct/f2(%/dat/d2%)', '/fct/f1']))

    def test_computing_cost_and_requests2(self):
        """Test if the cheapest cost and requests are computed correctly for a computation, where not all datapath are available"""
        self.fib.add_fib_entry(Name("/fct/f1"), [1])
        self.fib.add_fib_entry(Name("/dat"), [2])
        comp_str = '/fct/f1(/dat/data/d1,"Hello World",/fct/f2(/dat/d2))'
        name = Name("/fct/f1")
        name += '_(/dat/data/d1,"Hello World",/fct/f2(/dat/d2))'
        name += "NFN"
        ast = self.parser.parse(comp_str)
        name_list = self.thunklayer.generatePossibleThunkNames(ast)
        self.thunklayer.active_thunk_table.add_entry_to_thunk_table(name, 1, name_list)

        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[0], 10)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[1], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[2], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[3], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[4], 60)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[5], 20)
        self.thunklayer.active_thunk_table.add_estimated_cost_to_awaiting_data(name_list[6], 10)

        res = self.thunklayer.all_data_available(name)
        self.assertTrue(res)

        res = self.thunklayer.compute_cost_and_requests(ast, self.thunklayer.active_thunk_table.get_entry_from_name(name))
        self.assertEqual(res, (60, '/fct/f1(%/dat/data/d1%,"Hello World",/fct/f2(/dat/d2))'))

    def test_none_thunk_request_from_lower(self):
        """Test that a normal interest is forwared from lower to higher"""
        interest = Interest("/test/data")
        self.thunklayer.queue_from_lower.put([1, interest])
        res = self.thunklayer.queue_to_higher.get(timeout=2)
        self.assertEqual(res, [1, interest])

    def test_none_thunk_request_from_higher(self):
        """Test that a normal interest is forwared from higher to lower"""
        interest = Interest("/test/data")
        self.thunklayer.queue_from_higher.put([1, interest])
        res = self.thunklayer.queue_to_lower.get(timeout=2)
        self.assertEqual(res, [1, interest])

    def test_none_thunk_content_from_lower(self):
        """test that a normal content is forwared from lower to higher"""
        content = Content("/test/data")
        self.thunklayer.queue_from_lower.put([1, content])
        res = self.thunklayer.queue_to_higher.get(timeout=2)
        self.assertEqual(res, [1, content])

    def test_none_thunk_content_from_higher(self):
        """test that a normal content is forwared from higher to lower"""
        content = Content("/test/data")
        self.thunklayer.queue_from_higher.put([1, content])
        res = self.thunklayer.queue_to_lower.get(timeout=2)
        self.assertEqual(res, [1, content])

    def test_none_thunk_nack_from_lower(self):
        """test that a normal nack is forwared from lower to higher"""
        nack = Nack("/test/data", NackReason.NO_CONTENT, interest=Interest("/test/data"))
        self.thunklayer.queue_from_lower.put([1, nack])
        res = self.thunklayer.queue_to_higher.get(timeout=2)
        self.assertEqual(res, [1, nack])

    def test_none_thunk_nack_from_higher(self):
        """test that a normal nack is forwared from higher to lower"""
        nack = Nack("/test/data", NackReason.NO_CONTENT, interest=Interest("/test/data"))
        self.thunklayer.queue_from_higher.put([1, nack])
        res = self.thunklayer.queue_to_lower.get(timeout=2)
        self.assertEqual(res, [1, nack])

    def test_simple_thunk_request_from_lower(self):
        """test receiving a thunk request from the network"""
        self.thunklayer.fib.add_fib_entry(Name("/dat"), [2])
        self.thunklayer.fib.add_fib_entry(Name("/fct"), [1])

        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "THUNK"
        name += "NFN"
        interest = Interest(name)
        self.thunklayer.queue_from_lower.put([1,interest])

        res1 = self.thunklayer.queue_to_lower.get(timeout=2)
        res2 = self.thunklayer.queue_to_lower.get(timeout=2)
        res3 = self.thunklayer.queue_to_lower.get(timeout=2)
        res4 = self.thunklayer.queue_to_lower.get(timeout=2)

        self.assertEqual(res1, [1, Interest(Name('/fct/f1/THUNK'))])

        n2 = Name("/dat/data/d1")
        n2 += '/fct/f1(_)'
        n2 += 'THUNK'
        n2 += 'NFN'
        self.assertEqual(res2, [1, Interest(n2)])

        n3 = Name("/fct/f1")
        n3 += '_(/dat/data/d1)'
        n3 += 'THUNK'
        n3 += 'NFN'
        self.assertEqual(res3, [1, Interest(n3)])

        self.assertEqual(res4, [1, Interest(Name('/dat/data/d1/THUNK'))])

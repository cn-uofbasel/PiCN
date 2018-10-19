"""Test the BasicNFNLayer"""

import time
import unittest
import multiprocessing

from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNComputationTable import *
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict

class test_BasicNFNLayer(unittest.TestCase):
    """Test the BasicNFNLayer"""

    def setUp(self):
        #setup icn_layer
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("computation_table", NFNComputationList)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        self.r2cclient = TimeoutR2CHandler()
        parser = DefaultNFNParser()
        comp_table = synced_data_struct_factory.manager.computation_table(self.r2cclient, parser)

        self.executor = {"PYTHON": NFNPythonExecutor(None)}

        self.nfn_layer = BasicNFNLayer(cs, fib, pit, faceidtable, comp_table, self.executor, parser, self.r2cclient, log_level=255)

        self.nfn_layer.queue_to_lower = multiprocessing.Queue()
        self.nfn_layer.queue_from_lower = multiprocessing.Queue()

    def tearDown(self):
        pass

    def test_compute_no_params(self):
        """Test computing with a single function call"""
        computation_name = Name("/func/f1")
        computation_name += "_()"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f():\n    return 25"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "25"), res[1])

    def test_compute_single_param_int(self):
        """Test computing with a single function call and a single parameter, int"""
        computation_name = Name("/func/f1")
        computation_name += "_(21)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a):\n    return a*2"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "42"), res[1])

    def test_compute_params_int_str(self):
        """Test computing with a single function call and a int and str as parameter"""
        computation_name = Name("/func/f1")
        computation_name += "_(2,\"abc\")"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a,b):\n    return a*b"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "abcabc"), res[1])

    def test_compute_params_int_float(self):
        """Test computing with a single function call and int and float as parameter"""
        computation_name = Name("/func/f1")
        computation_name += "_(2,12.5)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a,b):\n    return a*b"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "25.0"), res[1])

    def test_compute_params_single_name(self):
        """Test computing with a single function call and one name as parameter"""
        computation_name = Name("/test/data")
        computation_name += "/func/f1(_)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/test/data")] = "Hello World"
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a):\n    return a.upper()"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "HELLO WORLD"), res[1])

    def test_compute_params_multiple_names(self):
        """Test computing with a single function call and one name as parameter"""
        computation_name = Name("/test/data")
        computation_name += "/func/f1(_,/data/test,2)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/test/data")] = "Hello World"
        computation_entry.available_data[Name("/data/test")] = "PICN"
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a,b,c):\n    return a.upper() " \
                                                             "+ ', ' +b.upper()*2"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "HELLO WORLD, PICNPICN"), res[1])

    def test_compute_recursive(self):
        """Test computing with a single function call and one name as parameter"""
        computation_name = Name("/test/data")
        computation_name += "/func/f1(/method/f2(_))"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        name2 = Name()
        name2 += "/method/f2(/test/data)"
        name2 += "NFN"

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f(a):\n    return a.upper() "
        computation_entry.available_data[name2] = "Hello World"

        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)

        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.compute(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(Content(computation_name, "HELLO WORLD"), res[1])

    def test_forwarding_descision_no_rewrite(self):
        """Test if forward or compute local: goal: forward with no rewrite"""
        self.nfn_layer.fib.add_fib_entry(Name('/func'), [1], True)

        computation_name = Name("/func/f1")
        computation_name += "_(/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], computation_interest)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).comp_state, NFNComputationState.REWRITE)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[-1], 'local')
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[0], "%/func/f1%(/test/data)")

    def test_forwarding_descision_rewrite(self):
        """Test if forward or compute local: goal: forward with rewrite"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        computation_name = Name("/func/f1")
        computation_name += "_(1,/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        compare_name = Name("/test/data")
        compare_name += "/func/f1(1,_)"
        compare_name += "NFN"
        self.assertEqual(res[1], Interest(compare_name))
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[-1], 'local')
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(1,%/test/data%)")

    def test_forward_descision_fwd_not_prepended_local(self):
        """Test if the forward or compute local: forward with not prepended data local available"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/test/data", "Hello World")
        self.nfn_layer.cs.add_content_object(c1)

        computation_name = Name("/func/f1")
        computation_name += "_(1,/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        compare_name = Name("/test/data")
        compare_name += "/func/f1(1,_)"
        compare_name += "NFN"
        self.assertEqual(res[1], Interest(compare_name))
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[-1], 'local')
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(1,%/test/data%)")

    def test_forward_descision_compute_local_no_param(self):
        """Test if the forward or compute local: goal: compute local with no parameter"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        self.nfn_layer.cs.add_content_object(c1)

        computation_name = Name("/func/f1")
        computation_name += "_()"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(Name("/func/f1")))

    def test_forward_descision_compute_local_param(self):
        """Test if the forward or compute local: goal: compute local with parameter"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        self.nfn_layer.cs.add_content_object(c1)

        computation_name = Name("/func/f1")
        computation_name += "_(1,/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(Name("/func/f1")))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(Name("/test/data")))
        self.assertTrue(self.nfn_layer.queue_to_lower.empty())

    def test_forward_descision_compute_inner_call(self):
        """Test if the forward or compute local: goal: compute local with inner call"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        self.nfn_layer.cs.add_content_object(c1)

        computation_name = Name("/func/f1")
        computation_name += "_(/func/f2(/test/data))"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)


        inner_computation_name = Name("/test/data")
        inner_computation_name += "/func/f2(_)"
        inner_computation_name += "NFN"
        inner_computation_interest = Interest(inner_computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(Name("/func/f1")))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], inner_computation_interest)
        self.assertTrue(self.nfn_layer.queue_to_lower.empty())

    def test_handle_interest(self):
        """Test if handle interest handles an interest message correctly"""

        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        self.nfn_layer.cs.add_content_object(c1)

        computation_name = Name("/func/f1")
        computation_name += "_(/func/f2(/test/data))"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)


        inner_computation_name = Name("/test/data")
        inner_computation_name += "/func/f2(_)"
        inner_computation_name += "NFN"
        inner_computation_interest = Interest(inner_computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        #self.nfn_layer.computation_table.append_computation(computation_entry) #TODO what does this line? reactive?

        self.nfn_layer.handleInterest(0, computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(Name("/func/f1")))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], inner_computation_interest)
        self.assertTrue(self.nfn_layer.queue_to_lower.empty())

    def test_handle_content_not_expected(self):
        """Test if a content object is handled correctly, if not expected"""
        content = Content("/test/data", "HelloWorld")
        self.nfn_layer.handleContent(1, content)
        res = self.nfn_layer.queue_to_lower.get()
        self.assertEqual(res, [1, content])

    def test_handle_content_expected(self):
        """Test if content object is handled correctly if expected"""
        computation_name = Name("/func/f1")
        computation_name += "_(1,/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)
        awaiting_name = Name("/test/data")

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.add_name_to_await_list(awaiting_name)
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data), 1)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).available_data), 0)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data[0].name, awaiting_name)

        self.nfn_layer.handleContent(1, Content("/test/data", "HelloWorld"))

        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data), 0)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).available_data), 1)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).available_data[awaiting_name], "HelloWorld")

    def test_handle_content_start_computation(self):
        """Test if content object is handled correctly if expected"""
        computation_name = Name("/func/f1")
        computation_name += "_(1,/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)
        awaiting_name = Name("/test/data")
        func_name = Name("/func/f1")

        computation_entry = NFNComputationTableEntry(computation_name, 1, computation_interest)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.add_name_to_await_list(awaiting_name)
        computation_entry.add_name_to_await_list(func_name)
        computation_entry.comp_state = NFNComputationState.EXEC
        self.nfn_layer.computation_table.append_computation(computation_entry)

        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data), 2)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).available_data), 0)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data[0].name, awaiting_name)

        self.nfn_layer.handleContent(1, Content(awaiting_name, "HelloWorld"))
        self.nfn_layer.handleContent(1, Content("/func/f1", "PYTHON\nf\ndef f(a,b):\n    return 2*b.upper()"))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res, [1, Content(computation_name, "HELLOWORLDHELLOWORLD")])

    def test_handle_content_start_fwd(self):
        """test rewrting handling content"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        computation_name = Name("/func/f1")
        computation_name += "_(/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.interest = computation_interest
        self.nfn_layer.computation_table.append_computation(computation_entry)

        compare_name = Name("/test/data")
        compare_name += "/func/f1(_)"
        compare_name += "NFN"

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(compare_name))
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).comp_state, NFNComputationState.REWRITE)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[-1], 'local')
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(%/test/data%)")

        self.nfn_layer.handleContent(res[0], Content(compare_name, "HelloWorld"))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([res[0], Content(computation_name, "HelloWorld")], res)

    def test_handle_nack_on_rewritten_computation_no_further_rewrite(self):
        """Test if a Nack message is handled correctly for a rewritten computation, when there is no further rewrite"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        computation_name = Name("/func/f1")
        computation_name += "_(/test/data)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.interest = computation_interest
        self.nfn_layer.computation_table.append_computation(computation_entry)

        compare_name = Name("/test/data")
        compare_name += "/func/f1(_)"
        compare_name += "NFN"

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(compare_name))
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).comp_state,
                         NFNComputationState.REWRITE)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list,
                         ["/func/f1(%/test/data%)", 'local'])

        self.nfn_layer.handleNack(res[1], Nack(compare_name, NackReason.COMP_PARAM_UNAVAILABLE,
                                               interest=Interest(compare_name)))

        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest("/func/f1"))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest("/test/data"))
        self.assertTrue(self.nfn_layer.queue_to_lower.empty())

    def test_handle_nack_on_rewritten_computation_further_rewrite(self):
        """Test if a Nack message is handled correctly for a rewritten computation, when there is a further rewrite"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)
        self.nfn_layer.fib.add_fib_entry(Name('/data'), [1], True)

        computation_name = Name("/func/f1")
        computation_name += "_(/test/data,/data/test)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.interest = computation_interest
        self.nfn_layer.computation_table.append_computation(computation_entry)

        nack_name = Name("/test/data")
        nack_name += "/func/f1(_,/data/test)"
        nack_name += "NFN"

        self.nfn_layer.forwarding_descision(computation_interest)
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(nack_name))
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).comp_state,
                         NFNComputationState.REWRITE)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 3)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list[-1], 'local')
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list,
                         ["/func/f1(%/test/data%,/data/test)", "/func/f1(/test/data,%/data/test%)", 'local'])

        self.nfn_layer.handleNack(res[1],
                                  Nack(nack_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=Interest(nack_name)))

        second_request_name = Name("/data/test")
        second_request_name += "/func/f1(/test/data,_)"
        second_request_name += "NFN"

        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(second_request_name))
        self.assertEqual(self.nfn_layer.computation_table.get_container_size(), 1)
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.nfn_layer.computation_table.get_computation(computation_name).rewrite_list,
                         ["/func/f1(/test/data,%/data/test%)", 'local'])

    def test_handle_nack_on_computation_name(self):
        """Test handle nack on the name of the original computation"""
        computation_name = Name("/func/f1")
        computation_name += "_(/test/data,/data/test)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.interest = computation_interest
        self.nfn_layer.computation_table.append_computation(computation_entry)
        self.assertEqual(self.nfn_layer.computation_table.get_container_size(), 1)
        self.nfn_layer.handleNack(1, Nack(computation_name, NackReason.COMP_PARAM_UNAVAILABLE,
                                          interest=computation_interest))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1],
                         Nack(computation_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=computation_interest))
        self.assertEqual(self.nfn_layer.computation_table.get_container(), [])

    def test_handle_nack_on_await_data(self):
        """Test handle nack on the name of awaiting data"""
        computation_name = Name("/func/f1")
        computation_name += "_(/test/data,/data/test)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_str, prepended = self.nfn_layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.nfn_layer.parser.parse(computation_str)
        computation_entry.interest = computation_interest
        self.nfn_layer.computation_table.append_computation(computation_entry)
        self.assertEqual(self.nfn_layer.computation_table.get_container_size(), 1)

        self.nfn_layer.computation_table.add_awaiting_data(computation_name, Name("/test/data"))
        self.assertEqual(len(self.nfn_layer.computation_table.get_computation(computation_name).awaiting_data), 1)

        self.nfn_layer.handleNack(1, Nack(Name("/test/data"), NackReason.NO_CONTENT,
                                          interest=Interest(Name("/test/data"))))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Nack(computation_name, NackReason.NO_CONTENT, interest=computation_interest))
        self.assertEqual(self.nfn_layer.computation_table.get_container(), [])

    def test_fwd(self):
        """Test forwarding using the BasicNFNLayer"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)
        self.nfn_layer.fib.add_fib_entry(Name('/data'), [1], True)

        self.nfn_layer.start_process()

        computation_name = Name("/func/f1")
        computation_name += "_(/test/data,/data/test)"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        self.nfn_layer.queue_from_lower.put([1, computation_interest])
        res1 = self.nfn_layer.queue_to_lower.get(timeout=2.0)

        res1_name = Name("/test/data")
        res1_name += "/func/f1(_,/data/test)"
        res1_name += "NFN"
        res1_interest = Interest(res1_name)
        self.assertEqual(res1[1], res1_interest)

        self.nfn_layer.queue_from_lower.put([1, Nack(res1_name, NackReason.NO_CONTENT, interest=res1_interest)])
        res2 = self.nfn_layer.queue_to_lower.get(timeout=2.0)

        res2_name = Name("/data/test")
        res2_name += "/func/f1(/test/data,_)"
        res2_name += "NFN"
        res2_interest = Interest(res2_name)
        self.assertEqual(res2[1], res2_interest)

        self.nfn_layer.queue_from_lower.put([1, Content(res2_name, "Hello World")])
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Content(computation_name, "Hello World"))
        self.assertTrue(self.nfn_layer.queue_to_lower.empty())

    def test_compute(self):
        """Test Computing using the BasicNFNLayer"""
        self.nfn_layer.fib.add_fib_entry(Name('/test'), [1], True)

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        self.nfn_layer.cs.add_content_object(c1)

        self.nfn_layer.start_process()

        computation_name = Name("/func/f1")
        computation_name += "_(/func/f2(/test/data))"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        self.nfn_layer.queue_from_lower.put([2, computation_interest])

        res1 = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res1, [2, Interest(Name("/func/f1"))])

        res2 = self.nfn_layer.queue_to_lower.get(timeout=2.0)

        inner_name = Name("/test/data")
        inner_name += "/func/f2(_)"
        inner_name += "NFN"
        inner_interest = Interest(inner_name)

        self.assertEqual(res2, [2, inner_interest])

        self.nfn_layer.queue_from_lower.put([2, c1])

        time.sleep(4)

        self.nfn_layer.ageing()
        res3 = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res3[1], inner_interest)

        r2c_name = Name("/test/data")
        r2c_name += "/func/f2(_)"
        r2c_name += "R2C"
        r2c_name += "KEEPALIVE"
        r2c_name += "NFN"
        r2c_interest = Interest(r2c_name)
        res4 = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res4[1], Content(r2c_name, 'Running'))

        self.nfn_layer.queue_from_lower.put([2, Content(inner_name, "HelloWorld")])
        res = self.nfn_layer.queue_to_lower.get()
        self.assertEqual(res[1], Content(computation_name, "HELLOWORLD"))

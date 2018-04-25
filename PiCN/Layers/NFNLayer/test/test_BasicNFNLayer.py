"""Test the BasicNFNLayer"""

import unittest
import multiprocessing

from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.NFNLayer.NFNComputationTable import *
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact


class test_BasicNFNLayer(unittest.TestCase):
    """Test the BasicNFNLayer"""

    def setUp(self):
        self.icn_data_structs = {}
        self.icn_data_structs['cs'] = ContentStoreMemoryExact()
        self.icn_data_structs['fib'] = ForwardingInformationBaseMemoryPrefix()
        self.icn_data_structs['pit'] = PendingInterstTableMemoryExact()

        self.executor = {"PYTHON": NFNPythonExecutor()}
        self.r2cclient = TimeoutR2CHandler()
        self.nfn_layer = BasicNFNLayer(self.icn_data_structs, self.executor)
        self.computation_table = self.nfn_layer.computation_table

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
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/func'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

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
        self.assertEqual(self.computation_table.get_computation(computation_name).comp_state, NFNComputationState.REWRITE)
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list[0], "%/func/f1%(/test/data)")

    def test_forwarding_descision_rewrite(self):
        """Test if forward or compute local: goal: forward with rewrite"""
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

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
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(1,%/test/data%)")

    def test_forward_descision_fwd_not_prepended_local(self):
        """Test if the forward or compute local: forward with not prepended data local available"""
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

        c1 = Content("/test/data", "Hello World")
        cs: ContentStoreMemoryExact = self.nfn_layer.icn_data_structs.get('cs')
        cs.add_content_object(c1)
        self.nfn_layer.icn_data_structs['cs'] = cs

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
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(1,%/test/data%)")

    def test_forward_descision_compute_local_no_param(self):
        """Test if the forward or compute local: goal: compute local with no parameter"""
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        cs: ContentStoreMemoryExact = self.nfn_layer.icn_data_structs.get('cs')
        cs.add_content_object(c1)
        self.nfn_layer.icn_data_structs['cs'] = cs

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
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        cs: ContentStoreMemoryExact = self.nfn_layer.icn_data_structs.get('cs')
        cs.add_content_object(c1)
        self.nfn_layer.icn_data_structs['cs'] = cs

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
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        cs: ContentStoreMemoryExact = self.nfn_layer.icn_data_structs.get('cs')
        cs.add_content_object(c1)
        self.nfn_layer.icn_data_structs['cs'] = cs

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

        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

        c1 = Content("/func/f1", "PYTHON\nf\ndef f(a):\n    return a.upper()")
        cs: ContentStoreMemoryExact = self.nfn_layer.icn_data_structs.get('cs')
        cs.add_content_object(c1)
        self.nfn_layer.icn_data_structs['cs'] = cs

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
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

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
        self.assertEqual(self.computation_table.get_computation(computation_name).comp_state, NFNComputationState.REWRITE)
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list[0], "/func/f1(%/test/data%)")

        self.nfn_layer.handleContent(res[0], Content(compare_name, "HelloWorld"))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([res[0], Content(computation_name, "HelloWorld")], res)

    def test_handle_nack_on_rewritten_computation_no_further_rewrite(self):
        """Test if a Nack message is handled correctly for a rewritten computation, when there is no further rewrite"""
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

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
        self.assertEqual(self.computation_table.get_computation(computation_name).comp_state,
                         NFNComputationState.REWRITE)
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list[0],
                         "/func/f1(%/test/data%)")

        self.nfn_layer.handleNack(res[1], Nack(compare_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=Interest(compare_name)))

        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Nack(computation_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=Interest(computation_name)))
        self.assertEqual(self.nfn_layer.computation_table.container, [])

    def test_handle_nack_on_rewritten_computation_further_rewrite(self):
        """Test if a Nack message is handled correctly for a rewritten computation, when there is a further rewrite"""
        fib: ForwardingInformationBaseMemoryPrefix = self.nfn_layer.icn_data_structs.get('fib')
        fib.add_fib_entry(Name('/test'), 1, True)
        fib.add_fib_entry(Name('/data'), 1, True)
        self.nfn_layer.icn_data_structs['fib'] = fib

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
        self.assertEqual(self.computation_table.get_computation(computation_name).comp_state,
                         NFNComputationState.REWRITE)
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 2)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list,
                         ["/func/f1(%/test/data%,/data/test)", "/func/f1(/test/data,%/data/test%)"])

        self.nfn_layer.handleNack(res[1], Nack(nack_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=Interest(nack_name)))

        second_request_name = Name("/data/test")
        second_request_name += "/func/f1(/test/data,_)"
        second_request_name += "NFN"

        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Interest(second_request_name))
        self.assertEqual(len(self.nfn_layer.computation_table.container), 1)
        self.assertEqual(len(self.computation_table.get_computation(computation_name).rewrite_list), 1)
        self.assertEqual(self.computation_table.get_computation(computation_name).rewrite_list,
                         ["/func/f1(/test/data,%/data/test%)"])

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
        self.assertEqual(len(self.computation_table.container), 1)
        self.nfn_layer.handleNack(1, Nack(computation_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=computation_interest))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Nack(computation_name, NackReason.COMP_PARAM_UNAVAILABLE, interest=computation_interest))
        self.assertEqual(self.nfn_layer.computation_table.container, [])

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
        self.assertEqual(len(self.computation_table.container), 1)

        self.nfn_layer.computation_table.add_awaiting_data(computation_name, Name("/test/data"))
        self.assertEqual(len(self.nfn_layer.computation_table.container[0].awaiting_data), 1)

        self.nfn_layer.handleNack(1, Nack(Name("/test/data"), NackReason.NO_CONTENT, interest=Interest(Name("/test/data"))))
        res = self.nfn_layer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res[1], Nack(computation_name, NackReason.NO_CONTENT, interest=computation_interest))
        self.assertEqual(self.nfn_layer.computation_table.container, [])

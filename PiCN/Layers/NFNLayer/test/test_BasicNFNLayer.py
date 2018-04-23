"""Test the BasicNFNLayer"""

import unittest
import multiprocessing

from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.NFNLayer.NFNComputationTable import *
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler

from PiCN.Packets import Name, Interest, Content

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
        self.computation_table = NFNComputationList(self.r2cclient)
        self.nfn_layer = BasicNFNLayer(self.icn_data_structs, self.executor, self.computation_table)

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

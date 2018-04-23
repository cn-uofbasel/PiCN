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

    def test_compute__params_int_str(self):
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

    def test_compute__params_int_float(self):
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

    def test_compute__params_names(self):
        """Test computing with a single function call and name as parameter"""
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
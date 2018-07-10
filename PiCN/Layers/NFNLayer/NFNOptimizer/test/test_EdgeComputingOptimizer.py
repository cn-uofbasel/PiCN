"""Testing the EdgeComputingOptimizers"""

import multiprocessing
import unittest

from PiCN.Packets import Name, Content
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact

from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer
from PiCN.Processes import PiCNSyncDataStructFactory


class test_ToDataFirstOptimizer(unittest.TestCase):
    """Testing the EdgeComputingOptimizers"""

    def setUp(self):
        self.parser: DefaultNFNParser = DefaultNFNParser()

        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("computation_table", NFNComputationList)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()

        self.r2cclient = TimeoutR2CHandler()
        parser = DefaultNFNParser()
        comp_table = synced_data_struct_factory.manager.computation_table(self.r2cclient, parser)

        self.optimizer: EdgeComputingOptimizer = EdgeComputingOptimizer(cs, fib, pit)


    def test_interest_fwd_comp_simple_interest(self):
        """Test the edgecomputing forwarder"""
        cmp_name = Name("/func/f1")
        cmp_name += "_()"
        cmp_name += "NFN"
        workflow = "/func/f1()"
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(cmp_name, ast))
        self.assertTrue(self.optimizer.compute_local(cmp_name, ast))
        rules = self.optimizer.rewrite(cmp_name, ast)
        self.assertEqual(rules, [])
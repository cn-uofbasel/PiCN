"""Testing the to Data First Optimizers"""

import multiprocessing
import unittest

from PiCN.Packets import Name, Content, Interest
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact

from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNOptimizer import MapReduceOptimizer
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict


class test_ToDataFirstOptimizer(unittest.TestCase):
    """Testing the to Data First Optimizers"""

    def setUp(self):
        self.parser: DefaultNFNParser = DefaultNFNParser()

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

        self.optimizer: MapReduceOptimizer = MapReduceOptimizer(cs, fib, pit, faceidtable)

    def tearDown(self):
        pass

    def test_simple_call_no_params_no_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter without fib"""
        workflow = "/func/f1()"
        ast = self.parser.parse(workflow)
        self.assertFalse(self.optimizer.compute_fwd(None, ast, Interest(workflow)))
        self.assertTrue(self.optimizer.compute_local(None, ast, Interest(workflow)))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['local'])


    def test_simple_call_no_params_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter"""
        cmp_name = Name("/func/f1")
        cmp_name += "_()"
        cmp_name += "NFN"
        workflow = "/func/f1()"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/func"), [1], False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(cmp_name, ast, Interest(cmp_name)))
        self.assertFalse(self.optimizer.compute_local(cmp_name, ast, Interest(cmp_name)))
        rules = self.optimizer.rewrite(cmp_name, ast)
        self.assertEqual(rules, ['%/func/f1%()', 'local'])

        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str, prepended = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)
        self.assertEqual(prepended, Name("/func/f1"))

    def test_simple_call_params_to_function(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to function"""
        cmp_name = Name("/func/f1")
        cmp_name += "_(/test/data)"
        cmp_name += "NFN"
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/func"), [1], False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast, Interest(cmp_name)))
        self.assertFalse(self.optimizer.compute_local(None, ast, Interest(cmp_name)))
        rules = self.optimizer.rewrite(cmp_name, ast)
        self.assertEqual(rules, ['%/func/f1%(/test/data)', 'local'])
        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str, prepended = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)
        self.assertEqual(prepended, Name("/func/f1"))

    def test_simple_call_params_to_function_local_prepended_data(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to function,
        compute local since prepended data are local"""
        cmp_name = Name("/func/f1")
        cmp_name += "_(/test/data)"
        cmp_name += "NFN"
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/func"), [1], False)
        self.optimizer.fib = fib
        prefix = Name("/func/f1")
        cs = self.optimizer.cs
        cs.add_content_object(
            Content(Name("/func/f1"), "PYTHON\nf\ndef f():\n    return 'Hello World'"),True)
        self.optimizer.cs = cs
        ast = self.parser.parse(workflow)
        self.assertFalse(self.optimizer.compute_fwd(prefix, ast, Interest(cmp_name)))
        self.assertTrue(self.optimizer.compute_local(prefix, ast, Interest(cmp_name)))
        rules = self.optimizer.rewrite(prefix, ast)
        self.assertEqual(rules, ['%/func/f1%(/test/data)', 'local'])
        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str, prepended = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)
        self.assertEqual(prepended, Name("/func/f1"))

    def test_simple_call_params_to_function_no_local_prepended_data(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to function,
        fwd since prepended data are not local"""
        cmp_name = Name("/func/f1")
        cmp_name._components.append("_(/test/data)")
        cmp_name._components.append("NFN")
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/func"), [1], False)
        self.optimizer.fib = fib
        self.optimizer.prefix = Name("/func/f1")
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast, Interest(cmp_name)))
        self.assertFalse(self.optimizer.compute_local(None, ast, Interest(cmp_name)))


    def test_simple_call_params_to_data(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to data"""
        cmp_name = Name("/test/data")
        cmp_name += "/func/f1(_)"
        cmp_name += "NFN"
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/test"), [1], False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast, Interest(cmp_name)))
        self.assertFalse(self.optimizer.compute_local(None, ast, Interest(cmp_name)))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)', 'local'])
        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str, prepended = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)
        self.assertEqual(prepended, Name("/test/data"))

    def test_simple_call_params(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter"""
        cmp_name1 = Name("/test/data")
        cmp_name1 += "/func/f1(_)"
        cmp_name1 += "NFN"
        cmp_name2 = Name("/func/f1")
        cmp_name2 += "_(/test/data)"
        cmp_name2 += "NFN"
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/test"), [1], False)
        fib.add_fib_entry(Name("/func"), [2], False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast, Interest(cmp_name1)))
        self.assertFalse(self.optimizer.compute_local(None, ast, Interest(cmp_name1)))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)', '%/func/f1%(/test/data)', 'local'])
        name1 = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name1, cmp_name1)
        name_str1, prepended1 = self.parser.network_name_to_nfn_str(name1)
        self.assertEqual(name_str1, workflow)
        self.assertEqual(prepended1, Name("/test/data"))
        name2 = self.parser.nfn_str_to_network_name(rules[1])
        self.assertEqual(name2, cmp_name2)
        name_str2, prepended2 = self.parser.network_name_to_nfn_str(name2)
        self.assertEqual(name_str2, workflow)
        self.assertEqual(prepended2, Name("/func/f1"))


    def test_multiple_calls_params(self):
        """Test, if ToDataFirstOptimizer works correctly with multiple function calls with parameter"""
        cmp_name1 = Name("/test/data")
        cmp_name1 = cmp_name1 + "/func/f1(_,/lib/f2(2,/data/test))"
        cmp_name1 = cmp_name1 + "NFN"
        cmp_name2 = Name("/lib/f2")
        cmp_name2 = cmp_name2 + "/func/f1(/test/data,_(2,/data/test))"
        cmp_name2 = cmp_name2 + "NFN"
        workflow = "/func/f1(/test/data,/lib/f2(2,/data/test))"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/lib"), [1], False)
        fib.add_fib_entry(Name("/test"), [2], False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast,  Interest(cmp_name1)))
        self.assertFalse(self.optimizer.compute_local(None, ast, Interest(cmp_name1)))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%,/lib/f2(2,/data/test))',
                                 '/func/f1(/test/data,%/lib/f2%(2,/data/test))', 'local'])
        name1 = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name1.to_string(), cmp_name1.to_string())
        name_str1, prepended1 = self.parser.network_name_to_nfn_str(name1)
        self.assertEqual(name_str1, workflow)
        self.assertEqual(prepended1,  Name("/test/data"))
        name2 = self.parser.nfn_str_to_network_name(rules[1])
        self.assertEqual(name2, cmp_name2)
        name_str2, prepended2 = self.parser.network_name_to_nfn_str(name2)
        self.assertEqual(name_str2, workflow)
        self.assertEqual(prepended2, Name("/lib/f2"))

    def test_split_control_flow(self):
        """test if the map reduce optimizer splits the control flow correctly"""
        fib_name1 = Name("/func/f2")
        fib_name2 = Name("/func/f3")
        fib = self.optimizer.fib
        fib.add_fib_entry(fib_name1, [1])
        fib.add_fib_entry(fib_name2, [2])
        self.optimizer.fib = fib


        comp = Name("/data/d1")
        comp += "/func/f1(/func/f2(_),/func/f3(/data/d2))"
        comp += "NFN"
        workflow = "/func/f1(/func/f2(/data/d1),/func/f3(/data/d2))"

        ast = self.parser.parse(str(workflow))
        self.assertNotEqual(ast, None)

        self.assertTrue(self.optimizer.compute_local(None, ast, Interest(comp)))
        self.assertFalse(self.optimizer.compute_fwd(None, ast, Interest(comp)))

        self.assertFalse(self.optimizer.compute_local(None, ast.params[0], None))
        self.assertTrue(self.optimizer.compute_fwd(None, ast.params[0], None))

        self.assertFalse(self.optimizer.compute_local(None, ast.params[1], None))
        self.assertTrue(self.optimizer.compute_fwd(None, ast.params[1], None))


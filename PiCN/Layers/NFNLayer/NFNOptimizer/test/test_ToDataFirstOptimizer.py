"""Testing the to Data First Optimizers"""

import multiprocessing
import unittest

from PiCN.Packets import Name, Content
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix

from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNOptimizer import ToDataFirstOptimizer

class test_ToDataFirstOptimizer(unittest.TestCase):
    """Testing the to Data First Optimizers"""

    def setUp(self):
        self.parser: DefaultNFNParser = DefaultNFNParser()
        self.manager = multiprocessing.Manager()
        self.data_structs = self.manager.dict()
        self.data_structs['cs'] = ContentStoreMemoryExact()
        self.data_structs['fib'] = ForwardingInformationBaseMemoryPrefix()
        self.optimizer: ToDataFirstOptimizer = ToDataFirstOptimizer(self.data_structs)

    def tearDown(self):
        pass

    def test_simple_call_no_params_no_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter without fib"""
        workflow = "/func/f1()"
        ast = self.parser.parse(workflow)
        self.assertFalse(self.optimizer.compute_fwd(None, ast))
        self.assertTrue(self.optimizer.compute_local(None, ast))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, [])


    def test_simple_call_no_params_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter"""
        cmp_name = Name("/func/f1")
        cmp_name += "_()"
        cmp_name += "NFN"
        workflow = "/func/f1()"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/func"), 1, False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(cmp_name, ast))
        self.assertFalse(self.optimizer.compute_local(cmp_name, ast))
        rules = self.optimizer.rewrite(cmp_name, ast)
        self.assertEqual(rules, ['%/func/f1%()'])

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
        fib.add_fib_entry(Name("/func"), 1, False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast))
        self.assertFalse(self.optimizer.compute_local(None, ast))
        rules = self.optimizer.rewrite(cmp_name, ast)
        self.assertEqual(rules, ['%/func/f1%(/test/data)'])
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
        fib.add_fib_entry(Name("/func"), 1, False)
        self.optimizer.fib = fib
        prefix = Name("/func/f1")
        cs = self.optimizer.cs
        cs.add_content_object(
            Content(Name("/func/f1"), "PYTHON\nf\ndef f():\n    return 'Hello World'"),True)
        self.optimizer.cs = cs
        ast = self.parser.parse(workflow)
        self.assertFalse(self.optimizer.compute_fwd(prefix, ast))
        self.assertTrue(self.optimizer.compute_local(prefix, ast))
        rules = self.optimizer.rewrite(prefix, ast)
        self.assertEqual(rules, ['%/func/f1%(/test/data)'])
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
        fib.add_fib_entry(Name("/func"), 1, False)
        self.optimizer.fib = fib
        self.optimizer.prefix = Name("/func/f1")
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast))
        self.assertFalse(self.optimizer.compute_local(None, ast))


    def test_simple_call_params_to_data(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to data"""
        cmp_name = Name("/test/data")
        cmp_name += "/func/f1(_)"
        cmp_name += "NFN"
        workflow = "/func/f1(/test/data)"
        fib = self.optimizer.fib
        fib.add_fib_entry(Name("/test"), 1, False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast))
        self.assertFalse(self.optimizer.compute_local(None, ast))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)'])
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
        fib.add_fib_entry(Name("/test"), 1, False)
        fib.add_fib_entry(Name("/func"), 2, False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast))
        self.assertFalse(self.optimizer.compute_local(None, ast))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)', '%/func/f1%(/test/data)'])
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
        fib.add_fib_entry(Name("/lib"), 1, False)
        fib.add_fib_entry(Name("/test"), 2, False)
        self.optimizer.fib = fib
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(None, ast))
        self.assertFalse(self.optimizer.compute_local(None, ast))
        rules = self.optimizer.rewrite(None, ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%,/lib/f2(2,/data/test))',
                                 '/func/f1(/test/data,%/lib/f2%(2,/data/test))'])
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




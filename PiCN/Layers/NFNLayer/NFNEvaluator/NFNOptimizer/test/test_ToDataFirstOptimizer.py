"""Testing the to Data First Optimizers"""

import multiprocessing
import unittest

from PiCN.Packets import Name
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer import ToDataFirstOptimizer

class test_ToDataFirstOptimizer(unittest.TestCase):
    """Testing the to Data First Optimizers"""

    def setUp(self):
        self.parser: DefaultNFNParser = DefaultNFNParser()
        self.manager = multiprocessing.Manager()
        self.optimizer: ToDataFirstOptimizer = ToDataFirstOptimizer(None, None,
                                                                    ForwardingInformationBaseMemoryPrefix(self.manager),
                                                                    None)



    def tearDown(self):
        pass

    def test_simple_call_no_params_no_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter without fib"""
        workflow = "/func/f1()"
        ast = self.parser.parse(workflow)
        self.assertFalse(self.optimizer.compute_fwd(ast))
        self.assertTrue(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, [])


    def test_simple_call_no_params_fib(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call without parameter"""
        cmp_name = Name("/func/f1")
        cmp_name._components.append("_()")
        cmp_name._components.append("NFN")
        workflow = "/func/f1()"
        self.optimizer.fib.add_fib_entry(Name("/func"), 1, False)
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(ast))
        self.assertFalse(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, ['%/func/f1%()'])

        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)

    def test_simple_call_params_to_function(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to function"""
        cmp_name = Name("/func/f1")
        cmp_name._components.append("_(/test/data)")
        cmp_name._components.append("NFN")
        workflow = "/func/f1(/test/data)"
        self.optimizer.fib.add_fib_entry(Name("/func"), 1, False)
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(ast))
        self.assertFalse(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, ['%/func/f1%(/test/data)'])
        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)

    def test_simple_call_params_to_data(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter, to data"""
        cmp_name = Name("/test/data")
        cmp_name._components.append("/func/f1(_)")
        cmp_name._components.append("NFN")
        workflow = "/func/f1(/test/data)"
        self.optimizer.fib.add_fib_entry(Name("/test"), 1, False)
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(ast))
        self.assertFalse(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)'])
        name = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name, cmp_name)
        name_str = self.parser.network_name_to_nfn_str(name)
        self.assertEqual(name_str, workflow)

    def test_simple_call_params(self):
        """Test, if ToDataFirstOptimizer works correctly with a single function call with parameter"""
        cmp_name1 = Name("/test/data")
        cmp_name1._components.append("/func/f1(_)")
        cmp_name1._components.append("NFN")
        cmp_name2 = Name("/func/f1")
        cmp_name2._components.append("_(/test/data)")
        cmp_name2._components.append("NFN")
        workflow = "/func/f1(/test/data)"
        self.optimizer.fib.add_fib_entry(Name("/test"), 1, False)
        self.optimizer.fib.add_fib_entry(Name("/func"), 2, False)
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(ast))
        self.assertFalse(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%)', '%/func/f1%(/test/data)'])
        name1 = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name1, cmp_name1)
        name_str1 = self.parser.network_name_to_nfn_str(name1)
        self.assertEqual(name_str1, workflow)
        name2 = self.parser.nfn_str_to_network_name(rules[1])
        self.assertEqual(name2, cmp_name2)
        name_str2 = self.parser.network_name_to_nfn_str(name2)
        self.assertEqual(name_str2, workflow)


    def test_multiple_calls_params(self):
        """Test, if ToDataFirstOptimizer works correctly with multiple function calls with parameter"""
        cmp_name1 = Name("/test/data")
        cmp_name1._components.append("/func/f1(_,/lib/f2(2,/data/test))")
        cmp_name1._components.append("NFN")
        cmp_name2 = Name("/lib/f2")
        cmp_name2._components.append("/func/f1(/test/data,_(2,/data/test))")
        cmp_name2._components.append("NFN")
        workflow = "/func/f1(/test/data,/lib/f2(2,/data/test))"
        self.optimizer.fib.add_fib_entry(Name("/lib"), 1, False)
        self.optimizer.fib.add_fib_entry(Name("/test"), 2, False)
        ast = self.parser.parse(workflow)
        self.assertTrue(self.optimizer.compute_fwd(ast))
        self.assertFalse(self.optimizer.compute_local(ast))
        rules = self.optimizer.rewrite(ast)
        self.assertEqual(rules, ['/func/f1(%/test/data%,/lib/f2(2,/data/test))',
                                 '/func/f1(/test/data,%/lib/f2%(2,/data/test))'])
        name1 = self.parser.nfn_str_to_network_name(rules[0])
        self.assertEqual(name1.to_string(), cmp_name1.to_string())
        name_str1 = self.parser.network_name_to_nfn_str(name1)
        self.assertEqual(name_str1, workflow)
        name2 = self.parser.nfn_str_to_network_name(rules[1])
        self.assertEqual(name2, cmp_name2)
        name_str2 = self.parser.network_name_to_nfn_str(name2)
        self.assertEqual(name_str2, workflow)





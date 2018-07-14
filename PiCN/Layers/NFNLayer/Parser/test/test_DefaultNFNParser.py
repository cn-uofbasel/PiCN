"""Test the default Parser"""

import unittest

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.Parser.AST import *


class test_DefaultNFNParser(unittest.TestCase):
    """Test the default Parser"""

    def setUp(self):
        self.parser = DefaultNFNParser()
        pass

    def tearDown(self):
        pass

    def test_parser_parsing_name(self):
        """Test the parser, parse a simple name"""
        string = "/test/data"
        ast = AST_Name("/test/data")

        res = self.parser.parse(string)
        self.assertTrue(isinstance(res, AST_Name))
        self.assertEqual(ast._element, res._element)

    def test_parser_parsing_simple_call(self):
        """Test the parser, parsing a simple call"""
        string = "/call/func(/test/data)"
        fc1 = AST_FuncCall("/call/func")
        param1 = AST_Name("/test/data")

        res: AST = self.parser.parse(string)
        self.assertTrue(isinstance(res, AST_FuncCall))
        self.assertEqual(fc1._element, res._element)
        self.assertEqual(len(res.params), 1)
        self.assertTrue(isinstance(res.params[0], AST_Name))
        self.assertEqual(param1._element, res.params[0]._element)

    def test_parser_parsing_simple_call_multiple_parameter(self):
        """Test the parser, parsing a simple call with multiple parameter"""
        string = "/call/func(/test/data,2,X)"
        fc1 = AST_FuncCall("/call/func")
        param1 = AST_Name("/test/data")
        param2 = AST_Int("2")
        param3 = AST_Var("X")

        res: AST = self.parser.parse(string)
        self.assertTrue(isinstance(res, AST_FuncCall))
        self.assertEqual(fc1._element, res._element)
        self.assertEqual(len(res.params), 3)
        self.assertTrue(isinstance(res.params[0], AST_Name))
        self.assertEqual(param1._element, res.params[0]._element)
        self.assertTrue(isinstance(res.params[1], AST_Int))
        self.assertEqual(param2._element, res.params[1]._element)
        self.assertTrue(isinstance(res.params[2], AST_Var))
        self.assertEqual(param3._element, res.params[2]._element)

    def test_parser_parsing_multiple_calls(self):
        """Test the parser, parsing multiple calls"""
        string = '/call/func(/lib/wcount("HelloWorld"))'
        fc1 = AST_FuncCall("/call/func")
        fc2 = AST_FuncCall("/lib/wcount")
        param1 = AST_String('"HelloWorld"')

        res: AST = self.parser.parse(string)
        self.assertTrue(isinstance(res, AST_FuncCall))
        self.assertEqual(fc1._element, res._element)
        self.assertEqual(len(res.params), 1)
        self.assertTrue(isinstance(res.params[0], AST_FuncCall))
        self.assertEqual(fc2._element, res.params[0]._element)
        self.assertEqual(len(res.params[0].params), 1)
        self.assertTrue(isinstance(res.params[0].params[0], AST_String))
        self.assertEqual(param1._element, res.params[0].params[0]._element)

    def test_parser_parsing_multiple_calls_multiple_parameter(self):
        """Test the parser, parsing multiple calls with multiple parameters"""
        string = '/call/func(3,/lib/wcount(/call/libfun(/test/data),"HelloWorld"))'
        fc1 = AST_FuncCall("/call/func")
        fc2 = AST_FuncCall("/lib/wcount")
        fc3 = AST_FuncCall("/call/libfun")
        param1 = AST_Int("3")
        param2 = AST_Int("/test/data")
        param3 = AST_String('"HelloWorld"')

        res: AST = self.parser.parse(string)
        self.assertTrue(isinstance(res, AST_FuncCall))
        self.assertEqual(fc1._element, res._element)
        self.assertEqual(len(res.params), 2)
        self.assertTrue(isinstance(res.params[0], AST_Int))
        self.assertEqual(param1._element, res.params[0]._element)
        self.assertTrue(isinstance(res.params[1], AST_FuncCall))
        self.assertEqual(fc2._element, res.params[1]._element)
        self.assertEqual(len(res.params[1].params), 2)
        self.assertTrue(isinstance(res.params[1].params[0], AST_FuncCall))
        self.assertEqual(fc3._element, res.params[1].params[0]._element)
        self.assertEqual(len(res.params[1].params[0].params), 1)
        self.assertTrue(isinstance(res.params[1].params[0].params[0], AST_Name))
        self.assertEqual(param2._element, res.params[1].params[0].params[0]._element)
        self.assertTrue(isinstance(res.params[1].params[1], AST_String))
        self.assertEqual(param3._element, res.params[1].params[1]._element)

    def test_parser_parsing_error1(self):
        """Test the parser, parsing call with syntax error 1"""
        string = "/call/func(/test/data"
        res: AST = self.parser.parse(string)
        self.assertEqual(res, None)

    def test_parser_parsing_error2(self):
        """Test the parser, parsing call with syntax error 2"""
        string = "/call/func(/test/data,/lib/call(X)"
        res: AST = self.parser.parse(string)
        self.assertEqual(res, None)

    def test_parser_parsing_error3(self):
        """Test the parser, parsing call with syntax error 3"""
        string = "call/func(/test/data)"
        res: AST = self.parser.parse(string)
        self.assertEqual(res, None)

    def test_ast_to_string(self):
        """Test converting the ast back to a string"""
        string = '/call/func(3,/lib/wcount(/call/libfun(/test/data),"HelloWorld"))'
        ast: AST = self.parser.parse(string)
        res = str(ast)
        self.assertEqual(string, res)

    def test_sub_ast_to_string(self):
        """Test converting the ast back to a string"""
        string = '/call/func(3,/lib/wcount(/call/libfun(/test/data),"HelloWorld"))'
        part_str = '/lib/wcount(/call/libfun(/test/data),"HelloWorld")'
        ast: AST = self.parser.parse(string)
        part_ast = ast.params[1]
        res = str(part_ast)
        self.assertEqual(part_str, res)

    def test_ast_to_string_nfn_marker(self):
        """Test converting the ast back to a string using nfn marker"""
        string = '/call/func(3,/lib/wcount(/call/libfun(/test/data),"HelloWorld"))'
        marked_str = '/call/func(3,%/lib/wcount%(/call/libfun(/test/data),"HelloWorld"))'
        ast: AST = self.parser.parse(string)
        ast.params[1]._prepend = True
        res = str(ast)
        self.assertEqual(marked_str, res)

    def test_network_name_to_nfn_str(self):
        """Test transforming network name to nfn str"""
        n = Name("/test/data")
        function_str = '/call/func(3,/lib/wcount(/call/libfun(_),"HelloWorld"))'
        cmp_str = '/call/func(3,/lib/wcount(/call/libfun(/test/data),"HelloWorld"))'
        n += function_str
        n += "NFN"
        res, prepended = self.parser.network_name_to_nfn_str(n)
        self.assertEqual(res, cmp_str)
        self.assertEqual(prepended, Name("/test/data"))

    def test_nfn_str_to_network_name(self):
        "Test transforming nfn str to network name"
        nfn_str = '/call/func(3,/lib/wcount(/call/libfun(%/test/data%),"HelloWorld"))'
        compname = Name("/test/data")
        function_str = '/call/func(3,/lib/wcount(/call/libfun(_),"HelloWorld"))'
        compname += function_str
        compname += "NFN"
        res = self.parser.nfn_str_to_network_name(nfn_str)
        self.assertEqual(res, compname)

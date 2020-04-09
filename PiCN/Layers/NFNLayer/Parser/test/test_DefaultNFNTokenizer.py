"""Test the default Tokenizer"""

import unittest

from PiCN.Layers.NFNLayer.Parser import TokenType
from PiCN.Layers.NFNLayer.Parser import Token
from PiCN.Layers.NFNLayer.Parser import DefaultNFNTokenizer

class test_DefaultNFNTokenizer(unittest.TestCase):
    """Test the default Tokenizer"""

    def setUp(self):
        self.stringToken = Token(TokenType.STRING, r'"', r'[A-Za-z0-9 :=]', r'"')
        self.intToken = Token(TokenType.INT, r'[0-9\+\-]', r'[0-9]', r'[0-9]')
        self.floatToken = Token(TokenType.FLOAT, r'[0-9\+\-]', r'[0-9.Ee]', r'[0-9]')
        self.nameToken = Token(TokenType.NAME, r'/', r'[A-Za-z0-9/.]', r'[A-Za-z0-9]')
        self.varToken = Token(TokenType.VAR, r'[A-Za-z0-9]', r'[A-Za-z0-9]', r'[A-Za-z0-9]')
        self.funcToken = Token(TokenType.FUNCCALL, r'/', r'[A-Za-z0-9/]', r'\(')
        self.endFuncToken = Token(TokenType.ENDFUNCCALL, r'\)', r'', r'')
        self.paramSeparator = Token(TokenType.PARAMSEPARATOR, r',', r'', r'')

        self.tokenizer = DefaultNFNTokenizer()
        self.tokenizer.add_token(self.stringToken)
        self.tokenizer.add_token(self.intToken)
        self.tokenizer.add_token(self.floatToken)
        self.tokenizer.add_token(self.nameToken)
        self.tokenizer.add_token(self.varToken)
        self.tokenizer.add_token(self.funcToken)
        self.tokenizer.add_token(self.endFuncToken)
        self.tokenizer.add_token(self.paramSeparator)

    def tearDown(self):
        pass

    def test_string(self):
        """Test single string"""
        test_string = '"teststring"'
        expected_res = [(TokenType.STRING, '"teststring"')]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_string2(self):
        """Test single string"""
        test_string = '"test string"'
        expected_res = [(TokenType.STRING, '"test string"')]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_string3(self):
        """Test single string"""
        test_string = '"=test string="'
        expected_res = [(TokenType.STRING, '"=test string="')]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_int(self):
        """Test single int"""
        test_string = "-1234"
        expected_res = [(TokenType.INT,"-1234")]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_float(self):
        """Test single float"""
        test_string = "2.5e8"
        expected_res = [(TokenType.FLOAT,"2.5e8")]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_name(self):
        """Test single float"""
        test_string = "/test/data"
        expected_res = [(TokenType.NAME, "/test/data")]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_name2(self):
        """Test single float"""
        test_string = "/test/data.txt"
        expected_res = [(TokenType.NAME, "/test/data.txt")]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_var(self):
        """Test single float"""
        test_string = "variable"
        expected_res = [(TokenType.VAR, "variable")]
        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_Tokenizer_simple_call(self):
        """Simple Test case for the Tokenizer"""
        test_string = '/call/func("test")'
        expected_res = [(TokenType.FUNCCALL, "/call/func("), (TokenType.STRING, '"test"'), (TokenType.ENDFUNCCALL, ')')]

        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_Tokenizer_simple_param_separator(self):
        """Test param separator"""
        test_string = '/call/func("test",/test/data)'
        expected_res = [(TokenType.FUNCCALL, "/call/func("), (TokenType.STRING, '"test"'),
                        (TokenType.PARAMSEPARATOR, ','), (TokenType.NAME, '/test/data'), (TokenType.ENDFUNCCALL, ')')]

        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

    def test_Tokenizer_error(self):
        """Test invalid string"""
        test_string = '/call/func("test'

        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(None, tokens)

    def test_Tokenizer_double_call(self):
        """Test a double call"""
        test_string = '/call/func(/test/data,/call/func2(2))'
        expected_res = [(TokenType.FUNCCALL, "/call/func("), (TokenType.NAME, '/test/data'),
                        (TokenType.PARAMSEPARATOR, ','), (TokenType.FUNCCALL, "/call/func2("), (TokenType.INT, "2"),
                        (TokenType.ENDFUNCCALL, ')'), (TokenType.ENDFUNCCALL, ')')]

        tokens = self.tokenizer.tokenize(test_string)
        self.assertEqual(expected_res, tokens)

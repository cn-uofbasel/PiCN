"""Test Name Object"""
import unittest

from PiCN.Packets import Name


class TestContent(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_names_equal(self):
        """Test if two names are equal"""
        n1 = Name("/test/data")
        n2 = Name("/test/data")
        self.assertEqual(n1, n2)

    def test_names_not_equal_name(self):
        """Test if two names objects are not equal: name"""
        n1 = Name("/test/data")
        n2 = Name("/test/data1")
        self.assertNotEqual(n1, n2)

    def test_constructor_str(self):
        n = Name('/test/data')
        self.assertEqual([b'test', b'data'], n._components)

    def test_constructor_byteslist(self):
        n = Name([b'test', b'data'])
        self.assertEqual([b'test', b'data'], n._components)
        self.assertEqual('/test/data', n.components_to_string())

    def test_constructor_unprintable(self):
        n = Name([bytes([0x01, 0x02, 0x03]), bytes([0xff, 0xfe, 0xdf])])

    def test_add_names(self):
        n1 = Name('/test')
        n2 = Name('/data')
        n = n1 + n2
        self.assertEqual([b'test', b'data'], n._components)
        self.assertEqual('/test/data', n.components_to_string())

    def test_add_str(self):
        n1 = Name('/test')
        n = n1 + 'data'
        self.assertEqual([b'test', b'data'], n._components)
        self.assertEqual('/test/data', n.components_to_string())

    def test_add_list(self):
        n1 = Name('/test')
        n = n1 + [b'data']
        self.assertEqual([b'test', b'data'], n._components)
        self.assertEqual('/test/data', n.components_to_string())

    def test_add_type_error(self):
        n1 = Name('/test')
        with self.assertRaises(TypeError):
            n1 + 42

    def test_add_inplace(self):
        n = Name('/test')
        n += 'data'
        self.assertEqual([b'test', b'data'], n._components)
        self.assertEqual('/test/data', n.components_to_string())

"""Test Packet Object"""
import unittest

from PiCN.Packets import Packet


class TestContent(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_packet_equal(self):
        """Test if two packet objects are equal"""
        p1 = Packet("/test/data")
        p1.name_payload = "Hello World"
        p2 = Packet("/test/data")
        p2.name_payload = "Hello World"
        self.assertEqual(p1, p2)

    def test_packet_not_equal_name(self):
        """Test if two packet objects are not equal: name"""
        p1 = Packet("/test/data")
        p2 = Packet("/test/data1")
        self.assertNotEqual(p1, p2)

        # disabled name payload in compare, since it breaks 1 content <-> 1 interest
        # def test_packet_not_equal_namepayload(self):
        #     """Test if two packet objects are not equal: payload"""
        #     p1 = Packet("/test/data")
        #     p1.name_payload = "Hello World"
        #     p2 = Packet("/test/data")
        #     p2.name_payload = "Hello World2"
        #     self.assertNotEqual(p1, p2)
        #
        #
        # def test_packet_not_equal_namepayload_not_available(self):
        #     """Test if two packet objects are not equal: payload once not available"""
        #     p1 = Packet("/test/data")
        #     p1.name_payload = "Hello World"
        #     p2 = Packet("/test/data")
        #     self.assertNotEqual(p1, p2)

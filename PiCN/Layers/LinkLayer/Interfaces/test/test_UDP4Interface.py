"""Test the UDP4 Interface"""

import socket
import unittest

from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface

class test_UDP4Interface(unittest.TestCase):
    """Test the UDP4 Interface"""

    def setUp(self):
        self.interface1 = UDP4Interface(0)
        self.interface2 = UDP4Interface(0)

    def tearDown(self):
        self.interface1.close()
        self.interface2.close()


    def test_receiving_data(self):
        """test receiving data"""
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind(("0.0.0.0", 0))
        port = self.interface1.get_port()

        test_sock.sendto(b"HelloWorld", ("127.0.0.1", port))

        data, addr = self.interface1.receive()

        self.assertEqual(data, b"HelloWorld")
        self.assertEqual(addr, ("127.0.0.1", test_sock.getsockname()[1]))

    def test_sending_data(self):
        "test sending data"
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_sock.bind(("0.0.0.0", 0))
        port = test_sock.getsockname()[1]

        self.interface1.send(b"HelloWorld", ("127.0.0.1", port))

        data, addr = test_sock.recvfrom(8192)

        self.assertEqual(data, b"HelloWorld")
        self.assertEqual(addr, ("127.0.0.1", self.interface1.get_port()))

    def test_send_receive(self):
        "test sending and receiving data"
        self.interface1.send(b"HelloWorld", ("127.0.0.1", self.interface2.get_port()))

        data, addr = self.interface2.receive()

        self.assertEqual(data, b"HelloWorld")
        self.assertEqual(addr, ("127.0.0.1", self.interface1.get_port()))
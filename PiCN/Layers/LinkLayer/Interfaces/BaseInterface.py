"""Abstract Superclass for a PiCN Interface"""

import abc


class AddressInfo(object):
    """Addressinfo describes how to send a packet using an address and an Interface"""
    def __init__(self, address, interface):
        self.address = address
        self.inferface = interface


class BaseInterface(object):
    """Abstract Superclass for a PiCN Interface"""

    def __init__(self):
        pass

    @abc.abstractmethod
    def send(self, data, addr):
        """send data to the specified address
        :param addr: addr to send the data to
        :param data: data to be sent
        """

    @abc.abstractmethod
    def receive(self):
        """receives data from the socket
        :return Tuple of received data and addr from which the data where received
        """

    @property
    @abc.abstractmethod
    def file_descriptor(self):
        """returns the file decribtor used for communication. This property is used by the LinkLayer to multiplex
        different sockets
        :return: File descriptor used for communication.
        """
"""Abstract Superclass for a PiCN Interface"""

import abc
from . import BaseInterface

class AddressInfo(object):
    """Addressinfo describes how to send a packet using an address and an Interface
    :param address: address information to send the packet. this information depend strongly on the interface type
    :param interface: interface corresponding to the address that should be used for sending
    """
    def __init__(self, address, interface_id: int):
        self.address = address
        self.interface_id = interface_id

    def __eq__(self, other):
        return self.address == other.address \
               and self.interface_id == other.interface_id

    def __hash__(self):
        return hash(self.address)  ^ hash(self.interface_id)

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
    def file_descriptor(self):
        """Returns the file descriptor used for communication. Historically used by
        BasicLinkLayer's SyncRunStrategy to multiplex sockets via select()/poll().

        Not part of the newer register()/send_async() async contract (see
        docs/design-adrs/ADR-008-baseinterface-contract.md and its 2026-08-04
        addendum) -- interfaces driven only by AsyncRunStrategy have no reason to
        support this and should not need to invent one. This default raises so a
        brand-new interface that has not overridden it fails loudly and points here,
        instead of mysteriously never receiving data. UDP4Interface and
        SimulationInterface both still override this with a real implementation,
        because they also support SyncRunStrategy today -- ADR-008's addendum.

        :return: File descriptor used for communication.
        :raises NotImplementedError: unless overridden by a subclass that still
            supports SyncRunStrategy.
        """
        raise NotImplementedError(
            "file_descriptor is not supported by this interface; it is only "
            "needed by BasicLinkLayer's SyncRunStrategy. See "
            "docs/design-adrs/ADR-008-baseinterface-contract.md."
        )

    def enable_broadcast(self) -> bool:
        """
        Attempts to enable broadcasting on this interface.  Must be overwritten if an interface implementation supports
        broadcast.

        :return: True on success, False on failure
        """
        return False

    def get_broadcast_address(self) -> str:
        """
        Get the interface's broadcast address. Broadcasting may have to be enabled first.

        :return: The interface's broadcast address, or None, if not applicable.
        """
        return None


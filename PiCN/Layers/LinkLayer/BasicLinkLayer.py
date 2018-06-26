"""Default Link Layer implementation for PiCN"""
import multiprocessing
import select

from PiCN.Processes import LayerProcess

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.LinkLayer.Interfaces import BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable


class BasicLinkLayer(LayerProcess):
    """Default Link Layer implementation for PiCN
    :param interface: preconfigured interface used to start the link layer
    :param faceidtable: faceidtable, that maintains the mapping between IDs and Interfaces
    """

    def __init__(self, interface: BaseInterface, faceidtable: BaseFaceIDTable):
        self.interfaces = []
        self.interfaces.append(interface)
        self.faeidtable = faceidtable

    def data_from_lower(self, interface: BaseInterface, to_higher: multiprocessing.Queue, data):
        """In the Linklayer, it handles received data, to lower is the network interface
        :param interface: Network interface, that received the data
        :param to_higher: queue to the higher layer
        :param data: received data
        """
        packet = data[0]
        addr = data[1]

        addr_info = AddressInfo(addr, interface)
        faceid = self.faeidtable.get_or_create_faceid(addr_info)
        to_higher.put([faceid, packet])

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """In the Linklayer, it handles data to be send, to lower is none, since an interface must be chosen
        :param to_lower: None
        :param to_higher: queue to the higher layer
        :param data: data to be send
        """
        faceid = data[0]
        packet = data[1]

        addr_info = self.faeidtable.get_address_info(faceid)
        addr_info.inferface.send(packet, addr_info.address)

    def handle_ready_fds(self, ready_fds, from_higher, to_higher, to_lower):
        """This method handles ready file decriptors
        :param ready_fds: ready file descriptors
        :param from_higher: queue from higher layer
        :param to_higher: queue to higher layer
        :param to_lower: queue to lower layer
        """
        for fd in ready_fds:
            if fd == from_higher._reader:
                data = from_higher.get()
                self.data_from_higher(to_lower, to_higher, data)
            else:
                interface = list(filter(lambda x: x.file_descriptor == fd, self.interfaces))[0]
                data = interface.receive()
                self.data_from_lower(interface, to_higher, data)

    def _run_poll(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                  to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        while True:
            poller = select.poll()
            READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
            fds = list(map(lambda x: x.file_descriptor, self.interfaces))
            for fd in fds:
                poller.register(fd)
            poller.register(from_higher)
            ready_fds = poller.poll()
            self.handle_ready_fds(ready_fds, from_higher, to_higher, to_lower)

    def _run_select(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                    to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        while True:
            fds = list(map(lambda x: x.file_descriptor, self.interfaces))
            fds.append(from_higher._reader)
            ready_fds = select.select(fds, [], [])
            self.handle_ready_fds(ready_fds, from_higher, to_higher, to_lower)

    def _run_sleep(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        super()._run_sleep(from_lower, from_higher, to_lower, to_higher)

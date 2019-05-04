"""Default Link Layer implementation for PiCN"""
import multiprocessing
import select
import socket

from typing import List

from PiCN.Processes import LayerProcess

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.LinkLayer.Interfaces import BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable


class BasicLinkLayer(LayerProcess):
    """Default Link Layer implementation for PiCN
    :param interface: preconfigured interfaces used by the link layer
    :param faceidtable: faceidtable, that maintains the mapping between IDs and Interfaces
    :param log_level: Loglevel used in the Linklayer
    """

    def __init__(self, interfaces: List[BaseInterface], faceidtable: BaseFaceIDTable, log_level=255):
        super().__init__(logger_name="LinkLayer", log_level=log_level)
        self.interfaces = interfaces
        self.faceidtable = faceidtable

    def data_from_lower(self, interface: BaseInterface, to_higher: multiprocessing.Queue, data):
        """In the Linklayer, it handles received data, to lower is the network interface
        :param interface: Network interface, that received the data
        :param to_higher: queue to the higher layer
        :param data: received data
        """
        ## OLD:
        packet = data[0]
        addr = data[1]
        #####
        print("Received Packet:")
        print(len(packet))
        print(packet)
        ## NEW:
        #udp_packet = data[0]
        #print(udp_packet)

        addr_info = AddressInfo(addr, self.interfaces.index(interface))
        faceid = self.faceidtable.get_or_create_faceid(addr_info)
        self.logger.info("Got data from Network and from Face ID: " + str(faceid) + ", addr: " + str(addr_info.address))
        to_higher.put([faceid, packet])

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """In the Linklayer, it handles data to be send, to lower is none, since an interface must be chosen
        :param to_lower: None
        :param to_higher: queue to the higher layer
        :param data: data to be send
        """

        faceid = data[0]
        packet = data[1]
        self.logger.info("Got data from Higher Layer with faceid: " + str(faceid))

        addr_info = self.faceidtable.get_address_info(faceid)
        if not addr_info:
            self.logger.error("No addr_info found for faceid: " + str(faceid))
            return
        self.interfaces[addr_info.interface_id].send(packet, addr_info.address)
        self.logger.info("Send packet to: " + str(addr_info.address))

    def _run_poll(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                  to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        while True:
            poller = select.poll()
            READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
            fds = list(map(lambda x: x.file_descriptor, self.interfaces))
            for fd in fds:
                poller.register(fd, READ_ONLY)
            poller.register(from_higher._reader, READ_ONLY)
            ready_fds = poller.poll()
            for fd in ready_fds:
                if fd[0] == from_higher._reader.fileno():
                    data = from_higher.get()
                    self.data_from_higher(to_lower, to_higher, data)
                else:
                    interfaces = list(filter(lambda x: x.file_descriptor.fileno() == fd[0], self.interfaces))
                    try:
                        interface = interfaces[0]
                    except:
                        return
                    data = interface.receive()
                    self.data_from_lower(interface, to_higher, data)

    def _run_select(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                    to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        while True:
            fds = list(map(lambda x: x.file_descriptor, self.interfaces))
            fds.append(from_higher._reader)
            ready_fds, _, _ = select.select(fds, [], [])
            for fd in ready_fds:
                if fd == from_higher._reader:
                    data = from_higher.get()
                    self.data_from_higher(to_lower, to_higher, data)
                else:
                    interfaces = list(filter(lambda x: x.file_descriptor == fd, self.interfaces))
                    try:
                        interface = interfaces[0]
                    except:
                        return
                    data = interface.receive()
                    self.data_from_lower(interface, to_higher, data)

    def _run_sleep(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        super()._run_sleep(from_lower, from_higher, to_lower, to_higher)
        #TODO this is not implemented
        raise NotImplemented()


    def stop_process(self):
        for i in self.interfaces:
            i.close()
        if self.process:
            self.process.terminate()
        if self.queue_to_higher:
            self.queue_to_higher.close()
        if self.queue_from_higher:
            self.queue_from_higher.close()

    def __del__(self):
        for i in self.interfaces:
            try:
                i.close()
            except:
                pass
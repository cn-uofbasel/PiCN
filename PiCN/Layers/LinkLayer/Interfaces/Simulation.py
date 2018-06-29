"""Simulation System for PiCN. The PiCN Simulation System consists of a Simulation Bus and Simulation Interfaces
The Simulation Bus is the dispatcher for different Simulation Interfaces. Each Simulation Interface has a unique address
which can be used as identify for a Face in the LinkLayer.
"""

import multiprocessing
import select

from typing import Dict

from PiCN.Processes import PiCNProcess
from PiCN.Layers.LinkLayer.Interfaces import BaseInterface


class SimulationInterface(BaseInterface):
    """A Simulation Interface manages the communication between a PiCN Forwarder and the Simulation Bus
    It can contain multiple parameter for packet loss or delay.
    """

    def __init__(self, address: str):
        self._address = address

        self.delay = lambda packet: 0  #Delay in microseconds
        self.packet_loss = lambda  packet: False  #False if packet is not lost

        self.queue_from_bus = multiprocessing.Queue()

        self.queue_from_linklayer = multiprocessing.Queue()

    def file_descriptor(self):
        return self.queue_from_bus._reader

    def send(self, data, addr):
        self.queue_from_bus.put([addr, data])

    def receive(self):
        return self.queue_from_linklayer.get(), self.address()

    def address(self):
        return self.address()



class SimulationBus(PiCNProcess):
    """Simulation Bus that dispatches the communication between nodes in a Simulation"""

    def __init__(self, interfacetable):
        self.interfacetable: Dict[SimulationInterface] = interfacetable

    def start_process(self):
        super().start_process()

    def stop_process(self):
        super().stop_process()

    def run(self):
        while True:
            poller = select.poll()
            READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
            fds = list(map((lambda x: x.file_descriptor), list(self.interfacetable.values())))
            for fd in fds:
                poller.register(fd, READ_ONLY)

            ready_fds = poller.poll()
            for fd in ready_fds:
                interfaces = list(filter(lambda x: x.file_descriptor.fileno() == fd[0], self.interfaces.values()))

            interfaces = list(filter(lambda x: x.file_descriptor.fileno() == fd[0], self.interfaces))
            try:
                interface = interfaces[0]
            except:
                return
            data = interface.receive()
            src_addr = interface.address()
            dst_addr = data[0]
            packet = data[1]

            if dst_addr not in self.interfacetable:
                continue

            #TODO delay(use thread timer) and packet loss (just continue)

            dst_interface: SimulationInterface = self.interfacetable.get(dst_addr)
            dst_interface.send(packet, src_addr)




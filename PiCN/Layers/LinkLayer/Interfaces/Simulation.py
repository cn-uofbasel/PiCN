"""Simulation System for PiCN. The PiCN Simulation System consists of a Simulation Bus and Simulation Interfaces
The Simulation Bus is the dispatcher for different Simulation Interfaces. Each Simulation Interface has a unique address
which can be used as identify for a Face in the LinkLayer.
"""

import multiprocessing
import select
import threading

from typing import Dict

from PiCN.Processes import PiCNProcess
from PiCN.Layers.LinkLayer.Interfaces import BaseInterface


class SimulationInterface(BaseInterface):
    """A Simulation Interface manages the communication between a PiCN Forwarder and the Simulation Bus
    It can contain multiple parameter for packet loss or delay.
    :param address: addr used by the interface
    """

    def __init__(self, address: str):
        self._address = address

        self.delay = lambda packet: 0  #Delay in microseconds
        self.packet_loss = lambda  packet: False  #False if packet is not lost

        self.queue_from_bus = multiprocessing.Queue()

        self.queue_from_linklayer = multiprocessing.Queue()

    @property
    def file_descriptor(self):
        return self.queue_from_bus._reader

    def send(self, data, addr, src = "relay"):
        if src == "relay":
            self.queue_from_linklayer.put([addr, data])
        elif src == "bus":
            self.queue_from_bus.put([addr, data])

    def receive(self, dst = "relay"):
        if dst == "relay":
            data = self.queue_from_bus.get()
        elif dst == "bus":
            data = self.queue_from_linklayer.get()
        addr = data[0]
        packet = data[1]
        return (packet, addr)

    def address(self):
        return self._address

    def close(self):
        self.queue_from_linklayer.close()
        self.queue_from_bus.close()



class SimulationBus(PiCNProcess):
    """Simulation Bus that dispatches the communication between nodes in a Simulation"""

    def __init__(self, ifacetable):
        self.interfacetable: Dict[SimulationInterface] = {}# ifacetable

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run)
        self.process.daemon = True
        self.process.start()

    def stop_process(self):
        if self.process:
            self.process.terminate()

    def _run(self):
        """Run the main loop of the Simulation Bus"""
        while True:
            poller = select.poll()
            READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
            fds = list(map((lambda x: x.queue_from_linklayer._reader), list(self.interfacetable.values())))
            for fd in fds:
                poller.register(fd, READ_ONLY)

            ready_fds = poller.poll()
            for fd in ready_fds:
                interfaces = list(filter(lambda x: x.queue_from_linklayer._reader.fileno() == fd[0], self.interfacetable.values()))
            try:
                interface = interfaces[0]
            except:
                return
            packet, dst_addr = interface.receive("bus")
            src_addr = interface.address()

            if dst_addr not in self.interfacetable:
                continue

            dst_interface: SimulationInterface = self.interfacetable.get(dst_addr)

            if dst_interface.packet_loss(packet):
                return

            delay = dst_interface.delay(packet)
            t = threading.Timer(delay, dst_interface.send, args=[packet, src_addr, "bus"])
            t.setDaemon(True)
            t.start()

    def add_interface(self, addr):
        """create a new interface given a addr and adds it to the
        :param addr: address to be used for the interface
        :return interface that was created.

        """
        iface = SimulationInterface(addr)
        self.interfacetable[addr] = iface
        return self.interfacetable.get(addr)


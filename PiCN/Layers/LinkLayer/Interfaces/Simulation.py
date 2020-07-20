"""Simulation System for PiCN. The PiCN Simulation System consists of a Simulation Bus and Simulation Interfaces
The Simulation Bus is the dispatcher for different Simulation Interfaces. Each Simulation Interface has a unique address
which can be used as identify for a Face in the LinkLayer.
"""

import multiprocessing
import select
import threading
import time
import logging

from sys import getsizeof
from typing import Dict

from PiCN.Logger import Logger
from PiCN.Processes import PiCNProcess
from PiCN.Layers.LinkLayer.Interfaces import BaseInterface
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder


class SimulationInterface(BaseInterface):
    """A Simulation Interface manages the communication between a PiCN Forwarder and the Simulation Bus
    It can contain multiple parameter for packet loss or delay.
    :param address: addr used by the interface
    :param bandwidth: maximum bandwidth for the interface, 0 for no limit
    :param delay_func: lambda-function, gets a packet as parameter and returns a delay value in seconds
    :param packet_loss_func: gets a packet as parameter and returns if the packet was lost (true) or not (false)
    """

    def __init__(self, address: str, max_bandwidth: int=0, delay_func=lambda packet: 0, packet_loss_func=lambda packet: False):
        self._address = address

        self.max_bandwidth = max_bandwidth #0 for infinite
        self.delay = delay_func #Delay in microseconds
        self.packet_loss = packet_loss_func  #False if packet is not lost

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

    def receive(self, dst = "relay", timeout=0):
        if dst == "relay":
            if timeout > 0:
                data = self.queue_from_bus.get(timeout=timeout)
            else:
                data = self.queue_from_bus.get()
        elif dst == "bus":
            if timeout > 0:
                data = self.queue_from_linklayer.get(timeout=timeout)
            else:
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

    def __init__(self, packetencoder: BasicEncoder=SimpleStringEncoder(), print_keep_alive=True,
                 log_level = logging.DEBUG):
        super().__init__("SimulationBus", log_level)
        self.interfacetable: Dict[str, SimulationInterface] = {}
        self.packetencoder = packetencoder
        self.print_keep_alive = print_keep_alive

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run)
        self.process.daemon = True
        self.process.start()

    def stop_process(self):
        for iface in self.interfacetable.values():
            iface.close()
        if self.process:
            self.process.terminate()

    def _run(self):
        """Run the main loop of the Simulation Bus"""
        time_interval = 3
        data_amount = 0
        timestamp = time.time()
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


            dec_packet = self.packetencoder.decode(packet)
            if self.print_keep_alive or (dec_packet.name.components[-1] == b'NFN' and dec_packet.name.components[-2] != b"KEEPALIVE"):
                self.logger.debug(f"{time.time():.5f}" + "\tSending packet from\t'" + src_addr + "'\tto\t'" + dst_addr + "':\t'" +
                      str(type(dec_packet)).replace("class ","").replace("PiCN.Packets.", "") + "\t"+
                      str(dec_packet.name).replace("\n", " ") + "'" )
                # print(f"{time.time():.5f}" + "\tSending packet from\t'" + src_addr + "'\tto\t'" + dst_addr + "':\t'" +
                #       str(type(dec_packet)).replace("class ","").replace("PiCN.Packets.", "") + "\t"+
                #       str(dec_packet.name).replace("\n", " ") + "'" , file=open("output.txt", "a")) #TODO improve logging

            dst_interface: SimulationInterface = self.interfacetable.get(dst_addr)

            if dst_interface.packet_loss(packet):
                if self.print_keep_alive or (dec_packet.name.components[-1] == b'NFN' and dec_packet.name.components[-2] != b"KEEPALIVE"):
                    self.logger.debug("\t... LOST")
                return

            if dst_interface.max_bandwidth > 0: #TODO check and improve that
                t = time.time()
                if timestamp + time_interval > t:
                    timestamp = time.time()
                    data_amount = 0
                elif data_amount * 1/time_interval > dst_interface.max_bandwidth:
                    time.sleep(time_interval - (t - timestamp))
                else:
                    data_amount += getsizeof(packet)

            delay = dst_interface.delay(packet)
            if self.print_keep_alive or (dec_packet.name.components[-1] == b'NFN' and dec_packet.name.components[-2] != b"KEEPALIVE"):
                self.logger.debug("\t(delay: " + str(delay) + ")")
            #t = threading.Timer(delay, dst_interface.send, args=[packet, src_addr, "bus"])
            #t.setDaemon(True)
            #t.start()
            time.sleep(delay)
            dst_interface.send(packet, src_addr, "bus")

    def add_interface(self, addr, max_bandwidth: int=0, delay_func=lambda packet: 0, packet_loss_func=lambda packet: False):
        """create a new interface given a addr and adds it to the
        :param addr: address to be used for the interface
        :param max_bandwidth: Maximum bandwith for the interface
        :param delay_func: lambda-function, gets a packet as parameter and returns a delay value in seconds
        :param packet_loss_func: gets a packet as parameter and returns if the packet was lost (true) or not (false)
        :return interface that was created.
        """
        iface = SimulationInterface(addr, max_bandwidth=max_bandwidth, delay_func=delay_func, packet_loss_func=packet_loss_func)
        self.interfacetable[addr] = iface
        return self.interfacetable.get(addr)






from typing import List, Tuple, Optional

import multiprocessing

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Processes import LayerProcess
from PiCN.Packets import Packet, Name
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigServerCore
from PiCN.Processes.Outbound import Outbound


class AutoconfigServerLayer(LayerProcess):

    def __init__(self,
                 linklayer: BasicLinkLayer,
                 address: str = '127.0.0.1',
                 registration_prefixes: List[Tuple[Name, bool]] = list(),
                 log_level: int = 255):
        """
        :param linklayer:
        :param address:
        :param log_level:
        """
        super().__init__(logger_name='AutoconfigLayer', log_level=log_level)
        self._core = AutoconfigServerCore(
            linklayer=linklayer,
            address=address,
            registration_prefixes=registration_prefixes,
            logger=self.logger,
        )

    @property
    def fib(self) -> BaseForwardingInformationBase:
        return self._core.fib

    @fib.setter
    def fib(self, value: BaseForwardingInformationBase):
        self._core.fib = value

    @property
    def rib(self) -> BaseRoutingInformationBase:
        return self._core.rib

    @rib.setter
    def rib(self, value: BaseRoutingInformationBase):
        self._core.rib = value

    def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            to_lower.put(out.item)
        elif out.direction == "higher":
            to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                self.queue_to_lower.put(out.item)
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                self.queue_to_higher.put(out.item)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info('Got data from lower')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        fid: int = data[0]
        addr_info: AddressInfo = self._core._linklayer.faceidtable.get_address_info(fid)
        packet: Packet = data[1]
        for out in self._core.handle_from_lower(fid, packet, addr_info):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

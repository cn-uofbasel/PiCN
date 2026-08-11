
from typing import List, Tuple

import multiprocessing
import threading
from datetime import timedelta

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.RoutingLayer.RoutingLayerCore import RoutingLayerCore
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound


class BasicRoutingLayer(LayerProcess):

    def __init__(self, linklayer: BasicLinkLayer,
                 peers: List[Tuple[str, int]] = None, log_level: int = 255):
        super().__init__('BasicRoutingLayer', log_level)
        self._core = RoutingLayerCore(linklayer=linklayer, peers=peers, logger=self.logger)
        self._ageing_interval: float = 5.0
        self._ageing_timer: threading.Timer = None

    @property
    def rib(self) -> BaseRoutingInformationBase:
        return self._core.rib

    @rib.setter
    def rib(self, value: BaseRoutingInformationBase):
        self._core.rib = value

    @property
    def fib(self) -> BaseForwardingInformationBase:
        return self._core.fib

    @fib.setter
    def fib(self, value: BaseForwardingInformationBase):
        self._core.fib = value

    def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            to_lower.put(out.item)
        elif out.direction == "higher":
            to_higher.put(out.item)
        elif out.direction == "queue_lower":
            if self.queue_to_lower is not None:
                try:
                    self.queue_to_lower.put(out.item)
                except AssertionError:
                    return
        elif out.direction == "queue_higher":
            if self.queue_to_higher is not None:
                self.queue_to_higher.put(out.item)

    def start_process(self):
        super().start_process()
        self._ageing()

    def stop_process(self):
        super().stop_process()
        if self._ageing_timer is not None:
            self._ageing_timer.cancel()
            self._ageing_timer = None

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_lower(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def _ageing(self):
        for out in self._core.ageing_and_solicit():
            self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
        self._ageing_timer = threading.Timer(self._ageing_interval, self._ageing)
        self._ageing_timer.start()

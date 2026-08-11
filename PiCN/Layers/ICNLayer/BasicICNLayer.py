"""Basic ICN Forwarding Layer"""

import multiprocessing
import threading
from typing import List

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ICNLayerCore import ICNLayerCore
from PiCN.Packets import Content, Interest, Nack
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound


class BasicICNLayer(LayerProcess):
    """ICN Forwarding Plane. Maintains data structures for ICN Forwarding

    Thin sync wrapper around :class:`ICNLayerCore` (ADR-003 extract-core).
    """

    def __init__(self, cs: BaseContentStore=None, pit: BasePendingInterestTable=None,
            fib: BaseForwardingInformationBase=None, rib: BaseRoutingInformationBase = None, log_level=255,
                 ageing_interval: int=3):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        self._core = ICNLayerCore(cs=cs, pit=pit, fib=fib, rib=rib, logger=self.logger)
        self._ageing_interval: int = ageing_interval

    @property
    def cs(self):
        return self._core.cs

    @cs.setter
    def cs(self, value):
        self._core.cs = value

    @property
    def pit(self):
        return self._core.pit

    @pit.setter
    def pit(self, value):
        self._core.pit = value

    @property
    def fib(self):
        return self._core.fib

    @fib.setter
    def fib(self, value):
        self._core.fib = value

    @property
    def rib(self):
        return self._core.rib

    @rib.setter
    def rib(self, value):
        self._core.rib = value

    @property
    def _interest_to_app(self) -> bool:
        return self._core._interest_to_app

    @_interest_to_app.setter
    def _interest_to_app(self, value: bool):
        self._core._interest_to_app = value

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

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_lower(data, has_to_higher=to_higher is not None):
            self._apply_outbound(out, to_lower, to_higher)

    def handle_interest_from_higher(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                                   to_higher: multiprocessing.Queue):
        for out in self._core.handle_interest_from_higher(face_id, interest):
            self._apply_outbound(out, to_lower, to_higher)

    def handle_interest_from_lower(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue,
                                   to_higher: multiprocessing.Queue, from_local: bool = False):
        for out in self._core.handle_interest_from_lower(
                face_id, interest, from_local=from_local, has_to_higher=to_higher is not None):
            self._apply_outbound(out, to_lower, to_higher)

    def handle_content(self, face_id: int, content: Content, to_lower: multiprocessing.Queue,
                       to_higher: multiprocessing.Queue, from_local: bool = False):
        for out in self._core.handle_content(
                face_id, content, from_local=from_local, has_to_higher=to_higher is not None):
            self._apply_outbound(out, to_lower, to_higher)

    def handle_nack(self, face_id: int, nack: Nack, to_lower: multiprocessing.Queue,
                    to_higher: multiprocessing.Queue, from_local: bool = False):
        for out in self._core.handle_nack(
                face_id, nack, from_local=from_local, has_to_higher=to_higher is not None):
            self._apply_outbound(out, to_lower, to_higher)

    def ageing(self):
        """Ageing the data structs"""
        try:
            for out in self._core.ageing():
                self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
        except Exception as e:
            # Matches pre-extract behaviour: Timer may fire after queues close.
            self.logger.warning("Exception during ageing: " + str(e))
            pass
        finally:
            t = threading.Timer(self._ageing_interval, self.ageing)
            t.daemon = True
            t.start()

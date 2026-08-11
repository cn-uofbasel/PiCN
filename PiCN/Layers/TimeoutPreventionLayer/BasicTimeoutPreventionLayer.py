"""BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
Moreover, it contains handler for incomming R2C messages"""

import multiprocessing
import threading

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Layers.TimeoutPreventionLayer.TimeoutPreventionCore import (
    TimeoutPreventionCore,
    TimeoutPreventionMessageDict,
)
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound

# Re-export for backward compatibility (tests, PiCNSyncDataStructFactory).
__all__ = ["TimeoutPreventionMessageDict", "BasicTimeoutPreventionLayer"]


class BasicTimeoutPreventionLayer(LayerProcess):
    """BasicR2CLayer maintains a list of messages for which R2C messages should be sent.
    Moreover, it contains handler for incomming R2C messages

    Thin sync wrapper around :class:`TimeoutPreventionCore` (ADR-003 extract-core).
    """

    def __init__(
        self,
        message_dict: TimeoutPreventionMessageDict,
        nfn_comp_table: BaseNFNComputationTable,
        pit: BasePendingInterestTable = None,
        log_level=255,
    ):
        super().__init__("TimeoutPrev", log_level)
        self._core = TimeoutPreventionCore(
            message_dict=message_dict,
            nfn_comp_table=nfn_comp_table,
            pit=pit,
            logger=self.logger,
        )

    @property
    def timeout_interval(self):
        return self._core.timeout_interval

    @timeout_interval.setter
    def timeout_interval(self, value):
        self._core.timeout_interval = value

    @property
    def ageing_interval(self):
        return self._core.ageing_interval

    @ageing_interval.setter
    def ageing_interval(self, value):
        self._core.ageing_interval = value

    @property
    def message_dict(self):
        return self._core.message_dict

    @property
    def computation_table(self):
        return self._core.computation_table

    @computation_table.setter
    def computation_table(self, value):
        self._core.computation_table = value

    @property
    def running_computations(self):
        return self._core.running_computations

    @property
    def pit(self):
        return self._core.pit

    @pit.setter
    def pit(self, value):
        self._core.pit = value

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
        for out in self._core.handle_from_lower(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def ageing(self):
        if self.queue_to_lower._closed or self.queue_to_higher._closed:
            return
        try:
            for out in self._core.ageing():
                self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
        finally:
            t = threading.Timer(self.ageing_interval, self.ageing)
            t.daemon = True
            t.start()

    def add_keep_alive_from_name(self, name):
        return self._core.add_keep_alive_from_name(name)

    def remove_keep_alive_from_name(self, name):
        return self._core.remove_keep_alive_from_name(name)

import multiprocessing
import threading
from typing import List, Optional

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Packets import Name, Packet, Interest
from PiCN.Processes import LayerProcess
from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigClientCore
from PiCN.Processes.Outbound import Outbound


class AutoconfigClientLayer(LayerProcess):

    def __init__(self, linklayer: BasicLinkLayer = None, bcport: int = 9000,
                 solicitation_timeout: float = None, solicitation_max_retry: int = 3, log_level: int = 255):
        """
        Create a new AutoconfigClientLayer.
        :param linklayer: The linklayer below, only needed to enable broadcasting on the UDP socket.
        :param bcport: The UDP port to broadcast on.
        :param solicitation_timeout: The timeout in seconds before a forwarder solicitation is resent. If this is None,
                                     a forwarder solicitation never times out, thus only a single one will be sent and
                                     no Nack will be generated if it remains unanswered.
        :param solicitation_max_retry: The maximum number of forwarder solicitations to send before sending a
                                       Nack NO_ROUTE upwards.
        """
        super().__init__('AutoconfigClientLayer', log_level=log_level)
        self._core = AutoconfigClientCore(
            linklayer=linklayer,
            bcport=bcport,
            solicitation_timeout=solicitation_timeout,
            solicitation_max_retry=solicitation_max_retry,
            logger=self.logger,
        )
        self._solicitation_timer: threading.Timer = None
        self._solicitation_max_retry: int = solicitation_max_retry

    @property
    def _solicitation_timeout(self) -> float:
        return self._core._solicitation_timeout

    @property
    def _linklayer(self) -> BasicLinkLayer:
        return self._core._linklayer

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

    def stop_process(self):
        super().stop_process()
        if self._solicitation_timer is not None:
            self._solicitation_timer.cancel()
            self._solicitation_timer = None

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from lower: {data}')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        fid, packet = data
        addr_info: AddressInfo = self._linklayer.faceidtable.get_address_info(fid)
        for out in self._core.handle_from_lower(fid, packet, addr_info):
            self._apply_outbound(out, to_lower, to_higher)
        if self._core.should_cancel_solicitation_timer():
            if self._solicitation_timer is not None:
                self._solicitation_timer.cancel()
                self._solicitation_timer = None

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from higher: {data}')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from higher layer')
            return
        if not isinstance(data[0], int) and data[0] is not None or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from higher layer')
            return
        fid: int = data[0]
        packet: Packet = data[1]
        outbounds, solicitation_started = self._core.handle_from_higher(fid, packet)
        for out in outbounds:
            self._apply_outbound(out, to_lower, to_higher)
        if solicitation_started and self._core.should_schedule_solicitation_retry(self._solicitation_max_retry):
            self._schedule_solicitation_timer(self._solicitation_max_retry - 1)

    def _schedule_solicitation_timer(self, retry: int):
        self._solicitation_timer = threading.Timer(
            self._core._solicitation_timeout,
            self._send_forwarder_solicitation,
            kwargs={'retry': retry},
        )
        self._solicitation_timer.start()

    def _send_forwarder_solicitation(self, retry: int):
        for out in self._core.send_forwarder_solicitation(retry):
            self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)
        if self._core.should_schedule_solicitation_retry(retry):
            self._schedule_solicitation_timer(retry - 1)

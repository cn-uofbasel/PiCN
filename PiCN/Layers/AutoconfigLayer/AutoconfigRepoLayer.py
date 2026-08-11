
import multiprocessing
import threading

from typing import List, Dict

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Packets import Name, Packet
from PiCN.Processes import LayerProcess
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.RepositoryLayer.Repository.BaseRepository import BaseRepository
from PiCN.Layers.AutoconfigLayer.AutoconfigLayerCore import AutoconfigRepoCore
from PiCN.Processes.Outbound import Outbound


class AutoconfigRepoLayer(LayerProcess):

    def __init__(self, name: str, linklayer: BasicLinkLayer, repo: BaseRepository,
                 addr: str, bcport: int = 9000,
                 register_local: bool = True, register_global: bool = False, log_level: int = 255):
        super().__init__('AutoconfigRepoLayer', log_level)
        self._core = AutoconfigRepoCore(
            name=name,
            linklayer=linklayer,
            repo=repo,
            addr=addr,
            bcport=bcport,
            register_local=register_local,
            register_global=register_global,
            logger=self.logger,
        )
        self._prefix_timers: Dict[Name, threading.Timer] = dict()

    @property
    def _register_local(self) -> bool:
        return self._core._register_local

    @_register_local.setter
    def _register_local(self, value: bool):
        self._core._register_local = value

    @property
    def _register_global(self) -> bool:
        return self._core._register_global

    @_register_global.setter
    def _register_global(self, value: bool):
        self._core._register_global = value

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

    def start_process(self):
        super().start_process()
        self.logger.info('Soliciting forwarders')
        for out in self._core.initial_forwarder_solicitations():
            self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

    def stop_process(self):
        super().stop_process()
        for timer in self._prefix_timers.values():
            timer.cancel()
        self._prefix_timers.clear()

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
        outbounds, renewals = self._core.handle_from_lower(fid, packet, addr_info)
        for out in outbounds:
            self._apply_outbound(out, to_lower, to_higher)
        for regname, renewal_addr_info, delay in renewals:
            timer = threading.Timer(delay, self._send_service_registration, [regname, renewal_addr_info])
            self._prefix_timers[regname] = timer
            timer.start()

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from higher: {data}')
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def _send_service_registration(self, name: Name, addr_info: AddressInfo):
        for out in self._core.send_service_registration(name, addr_info):
            self._apply_outbound(out, self.queue_to_lower, self.queue_to_higher)

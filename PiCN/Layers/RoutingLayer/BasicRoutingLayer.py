
from typing import List, Tuple

import multiprocessing
import threading
from datetime import datetime, timedelta

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Processes import LayerProcess
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseEntry
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Packets import Name, Content, Interest


class BasicRoutingLayer(LayerProcess):

    def __init__(self, linklayer: BasicLinkLayer,
                 peers: List[Tuple[str, int]] = None, log_level: int = 255):
        super().__init__('BasicRoutingLayer', log_level)
        self._prefix: Name = Name('/routing')
        self._linklayer: BasicLinkLayer = linklayer
        self.rib: BaseRoutingInformationBase = None
        self.fib: BaseForwardingInformationBase = None
        self._rib_maxage: timedelta = timedelta(seconds=3600)
        self._peers: List[Tuple[str, int]] = peers if peers is not None else []
        self._ageing_interval: float = 5.0
        self._ageing_timer: threading.Timer = None

    def start_process(self):
        super().start_process()
        self._ageing()

    def stop_process(self):
        super().stop_process()
        if self._ageing_timer is not None:
            self._ageing_timer.cancel()
            self._ageing_timer = None

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Received data from lower: {data}')
        if len(data) != 2:
            self.logger.warn('Expects [fid, Packet] from lower')
            return
        rcv_fid, packet = data
        now = datetime.utcnow()
        if packet.name == self._prefix:
            if isinstance(packet, Interest):
                self.logger.info('Received routing interest')
                output: str = ''
                for name, fid, dist, timeout in self.rib.entries():
                    if timeout is None:
                        output = f'{output}{name}:{dist}:-1\n'
                    else:
                        output = f'{output}{name}:{dist}:{int((timeout - now).total_seconds())}\n'
                content: Content = Content(self._prefix, output.encode('utf-8'))
                self.queue_to_lower.put([rcv_fid, content])
            elif isinstance(packet, Content):
                self.logger.info('Received routing content')
                rib: BaseRoutingInformationBase = self.rib
                lines: List[str] = [l for l in packet.content.split('\n') if len(l) > 0]
                for line in lines:
                    name, dist, timeout = line.rsplit(':', 2)
                    if timeout == '-1':
                        timeout = self._rib_maxage
                    else:
                        timeout = timedelta(seconds=int(timeout))
                    rib.insert(Name(name), rcv_fid, int(dist) + 1, now + min(timeout, self._rib_maxage))
            return
        self.queue_to_higher.put(data)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.queue_to_lower.put(data)

    def _ageing(self):
        if self.rib is not None:
            self.rib.ageing()
            self.fib.clear()
            for entry in self.rib.build_fib():
                self.fib.add_fib_entry(entry.name, [entry.faceid], static=entry.static)
        self._send_routing_interest()
        self._ageing_timer = threading.Timer(self._ageing_interval, self._ageing)
        self._ageing_timer.start()

    def _send_routing_interest(self):
        solicitation: Interest = Interest(self._prefix)
        for addr in self._peers:
            addr_info: AddressInfo = AddressInfo(addr, 0)
            fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info)
            try:
                self.queue_to_lower.put([fid, solicitation])
            except AssertionError:
                # Queue is closed.
                return

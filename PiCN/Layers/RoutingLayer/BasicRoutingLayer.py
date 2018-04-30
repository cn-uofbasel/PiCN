
from typing import List, Tuple, Dict

import multiprocessing
import threading
from datetime import datetime, timedelta

from PiCN.Processes import LayerProcess
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Packets import Name, Content, Interest


class BasicRoutingLayer(LayerProcess):

    def __init__(self, linklayer: UDP4LinkLayer, data_structs: Dict[str, object],
                 peers: List[Tuple[str, int]] = None, log_level: int = 255):
        super().__init__('BasicRoutingLayer', log_level)
        self._prefix: Name = Name('/routing')
        self._linklayer: UDP4LinkLayer = linklayer
        self._datastructs: Dict[str, object] = data_structs
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
        if packet.name == self._prefix:
            if isinstance(packet, Interest):
                self.logger.info('Received routing interest')
                rib: BaseRoutingInformationBase = self._datastructs['rib']
                output: str = ''
                for name, fid, dist in rib:
                    output = f'{output}{name}:{dist}\n'
                content: Content = Content(self._prefix, output.encode('utf-8'))
                self.queue_to_lower.put([rcv_fid, content])
            elif isinstance(packet, Content):
                self.logger.info('Received routing content')
                rib: BaseRoutingInformationBase = self._datastructs['rib']
                now: datetime = datetime.utcnow()
                lines: List[str] = [l for l in packet.content.split('\n') if len(l) > 0]
                # TODO(s3lph): Make rcv_fid static
                for line in lines:
                    name, dist = line.rsplit(':', 1)
                    rib.insert(Name(name), rcv_fid, int(dist) + 1, now + self._rib_maxage)
                self._datastructs['rib'] = rib
            return
        self.queue_to_higher.put(data)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.queue_to_lower.put(data)

    def _ageing(self):
        rib: BaseRoutingInformationBase = self._datastructs['rib']
        fib: BaseForwardingInformationBase = self._datastructs['fib']
        rib.ageing()
        rib.build_fib(fib)
        self._datastructs['rib'] = rib
        self._datastructs['fib'] = fib
        self._send_routing_interest()
        self._ageing_timer = threading.Timer(self._ageing_interval, self._ageing)
        self._ageing_timer.start()

    def _send_routing_interest(self):
        solicitation: Interest = Interest(self._prefix)
        for addr in self._peers:
            fid = self._linklayer.get_or_create_fid(addr, static=True)
            self.queue_to_lower.put([fid, solicitation])

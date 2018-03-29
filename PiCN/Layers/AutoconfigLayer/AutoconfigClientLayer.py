
import multiprocessing
import socket
from typing import List

from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Packets import Name, Packet, Interest, Content
from PiCN.Processes import LayerProcess

_AUTOCONFIG_PREFIX: Name = Name('/autoconfig')
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name('/autoconfig/forwarders')
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name('/autoconfig/services')
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name('/autoconfig/service')


class AutoconfigClientLayer(LayerProcess):

    def __init__(self, linklayer: UDP4LinkLayer = None, broadcast: str = '127.255.255.255', port: int = 9000,
                 log_level: int = 255):
        super().__init__('AutoconfigClientLayer', log_level=log_level)
        self._held_interests: List[Interest] = []
        self._linklayer: UDP4LinkLayer = linklayer
        self._broadcast_addr: str = broadcast
        self._broadcast_port: int = port

        # Enable broadcasting on the link layer's socket.
        if self._linklayer is not None:
            self._linklayer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from lower: {data}')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        packet: Packet = data[1]
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            to_higher.put(data)
            return
        if packet.name == _AUTOCONFIG_FORWARDERS_PREFIX:
            self._handle_forwarders(packet)

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
        if fid is not None:
            to_lower.put(data)
            return
        if isinstance(packet, Interest):
            self._held_interests.append(packet)
            autoconf: Interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)
            autoconf_fid = self._linklayer.get_or_create_fid((self._broadcast_addr, self._broadcast_port), static=True)
            to_lower.put([autoconf_fid, autoconf])

    def _handle_forwarders(self, packet: Packet):
        if not isinstance(packet, Content):
            return
        lines: List[str] = packet.content.split('\n')
        host, port = lines[0].split(':')
        fwd_fid = self._linklayer.get_or_create_fid((host, int(port)), static=True)
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            t, n = line.split(':')
            if t == 'r':
                name: Name = Name(n)
                for interest in self._held_interests:
                    if name.is_prefix_of(interest.name):
                        self.queue_to_lower.put([fwd_fid, interest])
                self._held_interests = [i for i in self._held_interests if not name.is_prefix_of(i.name)]

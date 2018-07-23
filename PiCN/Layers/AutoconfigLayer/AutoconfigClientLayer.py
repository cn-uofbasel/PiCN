import multiprocessing
import threading
from typing import List

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, UDP4Interface
from PiCN.Packets import Name, Packet, Interest, Content, Nack, NackReason
from PiCN.Processes import LayerProcess

_AUTOCONFIG_PREFIX: Name = Name('/autoconfig')
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name('/autoconfig/forwarders')
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name('/autoconfig/services')
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name('/autoconfig/service')


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
        self._held_interests: List[Interest] = []
        self._linklayer: BasicLinkLayer = linklayer
        self._bc_port = bcport
        self._solicitation_timeout: float = solicitation_timeout
        self._solicitation_max_retry: int = solicitation_max_retry
        self._solicitation_timer: threading.Timer = None

        self._bc_interfaces: List[int] = list()
        # Enable broadcasting on the link layer's socket.
        if self._linklayer is not None:
            for i in range(len(self._linklayer.interfaces)):
                interface = self._linklayer.interfaces[i]
                if interface.get_broadcast_address() is not None and interface.enable_broadcast():
                    self._bc_interfaces.append(i)

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
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            to_higher.put(data)
            return
        if packet.name == _AUTOCONFIG_FORWARDERS_PREFIX:
            self._handle_forwarders(packet, addr_info)

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
            self._send_forwarder_solicitation(self._solicitation_max_retry)

    def _handle_forwarders(self, packet: Packet, addr_info: AddressInfo):
        if not isinstance(packet, Content):
            return
        if len(packet.content) > 0 and packet.content[0] == 128:
            self.logger.error(f'This implementation cannot handle the autoconfig binary wire format.')
            return
        # Parse the received packet:
        # Parse the first line containing the forwarder's ip:port.
        lines: List[str] = packet.content.split('\n')
        scheme, addr = lines[0].split('://', 1)
        if scheme != 'udp4':
            self.logger.error(f'Don\'t know how to handle scheme {scheme} in forwarder advertisement.')
            return
        host, port = addr.split(':')
        fwd_addr = AddressInfo((host, int(port)), addr_info.interface_id)
        fwd_fid = self._linklayer.faceidtable.get_or_create_faceid(fwd_addr)
        # Parse the following lines of type:value pairs, only process routes.
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
        # Only cancel the forwarder solicitation timer if there are not held interests left.
        if self._solicitation_timer is not None and len(self._held_interests) == 0:
            self._solicitation_timer.cancel()
            self._solicitation_timer = None

    def _send_forwarder_solicitation(self, retry: int):

        autoconf: Interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)

        for i in self._bc_interfaces:
            interface = self._linklayer.interfaces[i]
            if not isinstance(interface, UDP4Interface):
                # Autoconfig currently only supported for UDP over IPv4
                continue
            interface: UDP4Interface = interface
            bcaddr: str = interface.get_broadcast_address()
            if bcaddr is not None:
                addr_info = AddressInfo((bcaddr, self._bc_port), i)
                autoconf_fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info)
                self.queue_to_lower.put([autoconf_fid, autoconf])

        # Schedule re-broadcast of the forwarder solicitation interest, which will recursively call this function.
        if self._solicitation_timeout is not None and retry > 1:
            self._solicitation_timer = threading.Timer(self._solicitation_timeout, self._send_forwarder_solicitation,
                                                       kwargs={'retry': retry - 1})
            self._solicitation_timer.start()
        elif retry <= 1:
            # If all forwarder solicitations timed out, send a Nack packet upwards for each held interest.
            for interest in self._held_interests:
                nack = Nack(interest.name, NackReason.NO_ROUTE, interest)
                self.queue_to_higher.put([None, nack])
            self._held_interests = []

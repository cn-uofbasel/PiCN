
import multiprocessing
import socket
from typing import List, Tuple
from datetime import datetime, timedelta

from PiCN.Processes import LayerProcess
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Packets import Packet, Interest, Content, Nack, NackReason, Name
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseEntry, BaseForwardingInformationBase


_AUTOCONFIG_PREFIX: Name = Name('/autoconfig')
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name('/autoconfig/forwarders')
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name('/autoconfig/services')
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name('/autoconfig/service')


class AutoconfigServerLayer(LayerProcess):

    def __init__(self, linklayer: UDP4LinkLayer = None, fib: BaseForwardingInformationBase = None,
                 address: str = '127.0.0.1', bcaddr: str = '255.255.255.255',
                 registration_prefixes: List[Tuple[Name, bool]] = list(), log_level: int = 255):
        """
        :param linklayer:
        :param fib:
        :param address:
        :param bcaddr:
        :param log_level:
        """
        super().__init__(logger_name='AutoconfigLayer', log_level=log_level)

        self._linklayer: UDP4LinkLayer = linklayer
        self._fib: BaseForwardingInformationBase = fib
        self._announce_addr: str = address
        self._broadcast_addr: str = bcaddr
        self._known_services: List[Tuple[Name, Tuple[str, int], datetime]] = []
        self._service_registration_prefixes: List[Tuple[Name, bool]] = registration_prefixes
        self._service_registration_timeout = timedelta(hours=1)

        # Enable broadcasting on the link layer's socket.
        if self._linklayer is not None:
            self._linklayer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info('Got data from lower')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        fid: int = data[0]
        packet: Packet = data[1]
        # Check whether data is autoconfig-related. If not, pass to ICN Layer.
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            to_higher.put(data)
        if isinstance(packet, Interest):
            if _AUTOCONFIG_FORWARDERS_PREFIX == packet.name:
                reply: Packet = self._handle_autoconfig(packet)
                to_lower.put([fid, reply])
            if _AUTOCONFIG_SERVICE_LIST_PREFIX.is_prefix_of(packet.name):
                reply: Packet = self._handle_service_list(packet)
                to_lower.put([fid, reply])
            if _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX.is_prefix_of(packet.name):
                reply: Packet = self._handle_service_registration(packet)
                to_lower.put([fid, reply])

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        # Simply pass all data from ICN layer down to Packet Encoding layer.
        to_lower.put(data)

    def _handle_autoconfig(self, interest: Interest) -> Packet:
        self.logger.info('Autoconfig information requested')
        port: int = self._linklayer.get_port()
        content: str = f'udp4://{self._announce_addr}:{port}\n'
        for entry in self._fib.container:
            entry: ForwardingInformationBaseEntry = entry
            content += f'r:{entry.name.to_string()}\n'
        for prefix, local in self._service_registration_prefixes:
            if local:
                content += f'pl:{prefix.to_string()}\n'
            else:
                content += f'pg:{prefix.to_string()}\n'
        reply: Content = Content(interest.name)
        reply.content = content.encode('utf-8')
        return reply

    def _handle_service_list(self, interest: Interest) -> Packet:
        self.logger.info('Service List requested')
        srvprefix = Name(interest.name.components[len(_AUTOCONFIG_SERVICE_LIST_PREFIX):])
        content = ''
        now: datetime = datetime.now()
        for service, _, timeout in self._known_services:
            service: Name = service
            timeout: datetime = timeout
            if now > timeout:
                continue
            if len(srvprefix) == 0 or srvprefix.is_prefix_of(service):
                content += f'{service.to_string()}\n'
        if len(content) > 0:
            self.logger.info(f'Sending list of services with prefix {srvprefix}')
            reply: Content = Content(interest.name)
            reply.content = content.encode('utf-8')
            return reply
        else:
            self.logger.info(f'No known services with prefix {srvprefix}, sending Nack')
            reply: Nack = Nack(interest.name, NackReason.NO_CONTENT)
            return reply

    def _handle_service_registration(self, interest: Interest) -> Packet:
        self.logger.info('Service Registration requested')
        remote: str = interest.name.components[len(_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX)].decode('ascii')
        self.logger.info(f'Remote service: {remote}')
        scheme, addr = remote.split('://', 1)
        if scheme != 'udp4':
            self.logger.error(f'Don\'t know how to handle scheme {scheme} in service registration.')
            nack: Nack = Nack(interest.name, NackReason.COMP_EXCEPTION)
            return nack
        host, port = addr.split(':')
        srvaddr = (host, int(port))
        srvname = Name(interest.name.components[len(_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX)+1:])
        if len([prefix[0] for prefix in self._service_registration_prefixes
                if len(prefix[0]) == 0 or prefix[0].is_prefix_of(srvname)]) == 0:
            nack: Nack = Nack(interest.name, NackReason.NO_ROUTE)
            nack.interest = interest
            return nack
        for i in range(len(self._known_services)):
            service, addr, _ = self._known_services[i]
            if service == srvname:
                if addr != srvaddr:
                    nack: Nack = Nack(interest.name, NackReason.DUPLICATE)
                    nack.interest = interest
                    return nack
                else:
                    self._known_services[i] = (service, addr, datetime.now() + self._service_registration_timeout)
                    ack: Content = Content(interest.name,
                                           str(int(self._service_registration_timeout.total_seconds())) + '\n')
                    return ack
        srvfid: int = self._linklayer.get_or_create_fid(srvaddr, static=True)
        self._fib.add_fib_entry(srvname, srvfid, static=True)
        self._known_services.append((srvname, srvaddr, datetime.now() + self._service_registration_timeout))
        ack: Content = Content(interest.name, str(int(self._service_registration_timeout.total_seconds())) + '\n')
        return ack

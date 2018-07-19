
import multiprocessing
import threading

from typing import List, Dict

from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, UDP4Interface
from PiCN.Packets import Name, Packet, Content, Interest, Nack
from PiCN.Processes import LayerProcess
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.RepositoryLayer.Repository.BaseRepository import BaseRepository

_AUTOCONFIG_PREFIX: Name = Name('/autoconfig')
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name('/autoconfig/forwarders')
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name('/autoconfig/services')
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name('/autoconfig/service')


class AutoconfigRepoLayer(LayerProcess):

    def __init__(self, name: str, linklayer: BasicLinkLayer, repo: BaseRepository,
                 addr: str, bcport: int = 9000,
                 register_local: bool = True, register_global: bool = False, log_level: int = 255):
        super().__init__('AutoconfigRepoLayer', log_level)
        self._linklayer = linklayer
        self._repository = repo
        self._addr: str = addr
        self._broadcast_port: int = bcport
        self._service_name: str = name
        self._prefix_timers: Dict[Name, threading.Timer] = dict()
        self._fwd_fid: int = None
        self._register_local: bool = register_local
        self._register_global: bool = register_global

        self._bc_interfaces: List[int] = list()
        # Enable broadcasting on the link layer's socket.
        if self._linklayer is not None:
            for i in range(len(self._linklayer.interfaces)):
                interface = self._linklayer.interfaces[i]
                if interface.get_broadcast_address() is not None and interface.enable_broadcast():
                    self._bc_interfaces.append(i)

    def start_process(self):
        super().start_process()
        self.logger.info('Soliciting forwarders')
        forwarders_interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)
        for i in self._bc_interfaces:
            interface = self._linklayer.interfaces[i]
            bcaddr: str = interface.get_broadcast_address()
            if bcaddr is not None:
                addr_info = AddressInfo((bcaddr, self._broadcast_port), i)
                autoconf_fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info,)
                self.queue_to_lower.put([autoconf_fid, forwarders_interest])

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
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            to_higher.put(data)
            return
        if _AUTOCONFIG_FORWARDERS_PREFIX.is_prefix_of(packet.name):
            addr_info = self._linklayer.faceidtable.get_address_info(fid)
            self._handle_forwarders(packet, addr_info)
        elif _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX.is_prefix_of(packet.name):
            self._handle_service_registration(packet, addr_info)
        pass

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from higher: {data}')
        to_lower.put(data)

    def _handle_forwarders(self, packet: Packet, addr_info: AddressInfo):
        if not isinstance(packet, Content):
            return
        self.logger.info('Received forwarder info')
        if len(packet.content) > 0 and packet.content[0] == 128:
            self.logger.error(f'This implementation cannot handle the autoconfig binary wire format.')
            return
        lines: List[str] = packet.content.split('\n')
        scheme, addr = lines[0].split('://', 1)
        if scheme != 'udp4':
            self.logger.error(f'Don\'t know how to handle scheme {scheme} in forwarder advertisement.')
            return
        host, port = addr.split(':')
        self.logger.info(f'forwarder: {host}:{port}')
        fwd_addr = AddressInfo((host, int(port)), addr_info.interface_id)
        self._fwd_fid = self._linklayer.faceidtable.get_or_create_faceid(fwd_addr)
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            t, n = line.split(':')
            if t == 'pl' and self._register_local:
                prefix = Name(n)
                self.logger.info(f'Got local prefix {prefix}, sending registration')
                self._send_service_registration(prefix + self._service_name, addr_info)
            if t == 'pg' and self._register_global:
                prefix = Name(n)
                self.logger.info(f'Got routed prefix {prefix}, sending registration')
                self._send_service_registration(prefix + self._service_name, addr_info)

    def _handle_service_registration(self, packet: Packet, addr_info: AddressInfo):
        if isinstance(packet, Nack):
            nack: Nack = packet
            self.logger.error(f'Service registration declined: {nack.reason}')
            return
        if isinstance(packet, Content):
            if packet.content is None:
                self.logger.error('Service Registration ACK without timeout')
                return
            if len(packet.content) > 0 and packet.content[0] == 137:
                self.logger.error('This implementation cannot handle the autoconfig binary wire format.')
                return
            regname = Name(packet.name.components[3:])
            try:
                timeout = int(packet.content)
                timer = threading.Timer(timeout / 2.0, self._send_service_registration, [regname, addr_info])
                self._prefix_timers[regname] = timer
                timer.start()
            except ValueError:
                self.logger.error('Service Registration ACK without timeout')
                return
            self.logger.info(f'Service registration accepted: {regname}')
            self._repository.set_prefix(regname)
            return

    def _send_service_registration(self, name: Name, addr_info: AddressInfo):
        interface = self._linklayer.interfaces[addr_info.interface_id]
        if not isinstance(interface, UDP4Interface):
            # Autoconfig currently only supported for UDP over IPv4
            return
        interface: UDP4Interface = interface
        registration_name: Name = _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX
        registration_name += f'udp4://{self._addr}:{interface.get_port()}'
        registration_name += name
        self.logger.info(f'Registering service {registration_name}')
        registration_interest = Interest(registration_name)
        self.logger.info('Sending service registration')
        self.queue_to_lower.put([self._fwd_fid, registration_interest])

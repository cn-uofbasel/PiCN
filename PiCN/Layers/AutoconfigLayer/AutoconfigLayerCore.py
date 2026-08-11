"""Shared autoconfig layer logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from PiCN.Layers.ICNLayer.ForwardingInformationBase import (
    BaseForwardingInformationBase,
    ForwardingInformationBaseEntry,
)
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, UDP4Interface
from PiCN.Layers.RepositoryLayer.Repository.BaseRepository import BaseRepository
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Nack, NackReason, Name, Packet
from PiCN.Processes.Outbound import Outbound

_AUTOCONFIG_PREFIX: Name = Name("/autoconfig")
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name("/autoconfig/forwarders")
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name("/autoconfig/services")
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name("/autoconfig/service")


class AutoconfigServerCore:
    """Autoconfig server (forwarder advertisement, service list, registration)."""

    def __init__(
        self,
        linklayer: BasicLinkLayer,
        address: str = "127.0.0.1",
        registration_prefixes: List[Tuple[Name, bool]] = list(),
        service_registration_timeout: timedelta = timedelta(hours=1),
        logger: Optional[Logger] = None,
    ):
        self._linklayer: BasicLinkLayer = linklayer
        self.fib: BaseForwardingInformationBase = None
        self.rib: BaseRoutingInformationBase = None
        self._announce_addr: str = address
        self._known_services: List[Tuple[Name, Tuple[str, int], datetime]] = []
        self._service_registration_prefixes: List[Tuple[Name, bool]] = registration_prefixes
        self._service_registration_timeout = service_registration_timeout
        self._bc_interfaces: List[int] = []
        if self._linklayer is not None:
            for i in range(len(self._linklayer.interfaces)):
                interface = self._linklayer.interfaces[i]
                if interface.enable_broadcast():
                    self._bc_interfaces.append(i)
        self.logger = logger if logger is not None else Logger("AutoconfigServerCore", 255)

    def handle_from_lower(self, fid: int, packet: Packet, addr_info: AddressInfo) -> List[Outbound]:
        out: List[Outbound] = []
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            out.append(Outbound("higher", [fid, packet]))
        if isinstance(packet, Interest):
            if _AUTOCONFIG_FORWARDERS_PREFIX == packet.name:
                reply: Optional[Packet] = self._handle_autoconfig(packet, addr_info)
                if reply is not None:
                    out.append(Outbound("lower", [fid, reply]))
            if _AUTOCONFIG_SERVICE_LIST_PREFIX.is_prefix_of(packet.name):
                reply = self._handle_service_list(packet)
                out.append(Outbound("lower", [fid, reply]))
            if _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX.is_prefix_of(packet.name):
                reply = self._handle_service_registration(packet, addr_info)
                out.append(Outbound("lower", [fid, reply]))
        return out

    def handle_from_higher(self, data) -> List[Outbound]:
        return [Outbound("lower", data)]

    def _handle_autoconfig(self, interest: Interest, addr_info: AddressInfo) -> Optional[Packet]:
        self.logger.info("Autoconfig information requested")
        interface = self._linklayer.interfaces[addr_info.interface_id]
        if not isinstance(interface, UDP4Interface):
            return None
        interface: UDP4Interface = interface
        port: int = interface.get_port()
        content: str = f"udp4://{self._announce_addr}:{port}\n"
        for entry in self.fib.get_container():
            entry: ForwardingInformationBaseEntry = entry
            content += f"r:{entry.name.to_string()}\n"
        for prefix, local in self._service_registration_prefixes:
            if local:
                content += f"pl:{prefix.to_string()}\n"
            else:
                content += f"pg:{prefix.to_string()}\n"
        reply: Content = Content(interest.name)
        reply.content = content.encode("utf-8")
        return reply

    def _handle_service_list(self, interest: Interest) -> Packet:
        self.logger.info("Service List requested")
        srvprefix = Name(interest.name.components[len(_AUTOCONFIG_SERVICE_LIST_PREFIX):])
        content = ""
        now: datetime = datetime.now(timezone.utc)
        for service, _, timeout in self._known_services:
            service: Name = service
            timeout: datetime = timeout
            if now > timeout:
                continue
            if len(srvprefix) == 0 or srvprefix.is_prefix_of(service):
                content += f"{service.to_string()}\n"
        if len(content) > 0:
            self.logger.info(f"Sending list of services with prefix {srvprefix}")
            reply: Content = Content(interest.name)
            reply.content = content.encode("utf-8")
            return reply
        self.logger.info(f"No known services with prefix {srvprefix}, sending Nack")
        reply: Nack = Nack(interest.name, NackReason.NO_CONTENT, interest)
        return reply

    def _handle_service_registration(self, interest: Interest, addr_info: AddressInfo) -> Packet:
        self.logger.info("Service Registration requested")
        remote: str = interest.name.components[len(_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX)].decode("ascii")
        self.logger.info(f"Remote service: {remote}")
        scheme, addr = remote.split("://", 1)
        if scheme != "udp4":
            self.logger.error(f"Don't know how to handle scheme {scheme} in service registration.")
            nack: Nack = Nack(interest.name, NackReason.COMP_EXCEPTION, interest)
            return nack
        host, port = addr.split(":")
        srvaddr = (host, int(port))
        srvname = Name(interest.name.components[len(_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX) + 1:])
        prefix_candidates = [
            prefix
            for prefix in self._service_registration_prefixes
            if len(prefix[0]) == 0 or prefix[0].is_prefix_of(srvname)
        ]
        if len(prefix_candidates) == 0:
            nack: Nack = Nack(interest.name, NackReason.NO_ROUTE, interest)
            nack.interest = interest
            return nack
        prefix_candidates.sort(key=lambda p: len(p[0]), reverse=True)
        registration_prefix, local_only = prefix_candidates[0]

        now = datetime.now(timezone.utc)
        timeout = now + self._service_registration_timeout

        for i in range(len(self._known_services)):
            service, addr, srvtimeout = self._known_services[i]
            if srvtimeout <= now:
                continue
            if service == srvname:
                if addr != srvaddr:
                    nack: Nack = Nack(interest.name, NackReason.DUPLICATE, interest)
                    nack.interest = interest
                    return nack
                self._known_services[i] = (service, addr, timeout)
                ack: Content = Content(
                    interest.name,
                    str(int(self._service_registration_timeout.total_seconds())) + "\n",
                )
                return ack
        srv_addr_info = AddressInfo(srvaddr, addr_info.interface_id)
        srvfid: int = self._linklayer.faceidtable.get_or_create_faceid(srv_addr_info)
        if local_only or self.rib is None:
            self.fib.add_fib_entry(srvname, [srvfid], static=True)
        else:
            self.rib.insert(srvname, srvfid, 1, timeout)
            container: List[ForwardingInformationBaseEntry] = self.fib.container
            container = self.rib.build_fib(container)
            self.fib.container = container
        self._known_services.append(
            (srvname, srvaddr, datetime.now(timezone.utc) + self._service_registration_timeout)
        )
        ack: Content = Content(
            interest.name,
            str(int(self._service_registration_timeout.total_seconds())) + "\n",
        )
        return ack


class AutoconfigClientCore:
    """Autoconfig client (forwarder solicitation and held interests)."""

    def __init__(
        self,
        linklayer: BasicLinkLayer = None,
        bcport: int = 9000,
        solicitation_timeout: float = None,
        solicitation_max_retry: int = 3,
        logger: Optional[Logger] = None,
    ):
        self._held_interests: List[Interest] = []
        self._linklayer: BasicLinkLayer = linklayer
        self._bc_port = bcport
        self._solicitation_timeout: float = solicitation_timeout
        self._solicitation_max_retry: int = solicitation_max_retry
        self._bc_interfaces: List[int] = []
        if self._linklayer is not None:
            for i in range(len(self._linklayer.interfaces)):
                interface = self._linklayer.interfaces[i]
                if interface.get_broadcast_address() is not None and interface.enable_broadcast():
                    self._bc_interfaces.append(i)
        self.logger = logger if logger is not None else Logger("AutoconfigClientCore", 255)

    @property
    def held_interests(self) -> List[Interest]:
        return self._held_interests

    def handle_from_lower(self, fid: int, packet: Packet, addr_info: AddressInfo) -> List[Outbound]:
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            return [Outbound("higher", [fid, packet])]
        if packet.name == _AUTOCONFIG_FORWARDERS_PREFIX:
            return self._handle_forwarders(packet, addr_info)
        return []

    def handle_from_higher(self, fid: Optional[int], packet: Packet) -> Tuple[List[Outbound], bool]:
        """Returns outbounds and whether to start forwarder solicitation."""
        if fid is not None:
            return [Outbound("lower", [fid, packet])], False
        if isinstance(packet, Interest):
            self._held_interests.append(packet)
            return self.send_forwarder_solicitation(self._solicitation_max_retry), True
        return [], False

    def send_forwarder_solicitation(self, retry: int) -> List[Outbound]:
        out: List[Outbound] = []
        autoconf: Interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)
        for i in self._bc_interfaces:
            interface = self._linklayer.interfaces[i]
            if not isinstance(interface, UDP4Interface):
                continue
            interface: UDP4Interface = interface
            bcaddr: str = interface.get_broadcast_address()
            if bcaddr is not None:
                addr_info = AddressInfo((bcaddr, self._bc_port), i)
                autoconf_fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info)
                out.append(Outbound("queue_lower", [autoconf_fid, autoconf]))
        if retry <= 1 and self._solicitation_timeout is not None:
            for interest in self._held_interests:
                nack = Nack(interest.name, NackReason.NO_ROUTE, interest)
                out.append(Outbound("queue_higher", [None, nack]))
            self._held_interests = []
        return out

    def should_schedule_solicitation_retry(self, retry: int) -> bool:
        return self._solicitation_timeout is not None and retry > 1

    def _handle_forwarders(self, packet: Packet, addr_info: AddressInfo) -> List[Outbound]:
        out: List[Outbound] = []
        if not isinstance(packet, Content):
            return out
        if len(packet.content) > 0 and packet.content[0] == 128:
            self.logger.error("This implementation cannot handle the autoconfig binary wire format.")
            return out
        lines: List[str] = packet.content.split("\n")
        scheme, addr = lines[0].split("://", 1)
        if scheme != "udp4":
            self.logger.error(f"Don't know how to handle scheme {scheme} in forwarder advertisement.")
            return out
        host, port = addr.split(":")
        fwd_addr = AddressInfo((host, int(port)), addr_info.interface_id)
        fwd_fid = self._linklayer.faceidtable.get_or_create_faceid(fwd_addr)
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            t, n = line.split(":")
            if t == "r":
                name: Name = Name(n)
                for interest in self._held_interests:
                    if name.is_prefix_of(interest.name):
                        out.append(Outbound("queue_lower", [fwd_fid, interest]))
                self._held_interests = [i for i in self._held_interests if not name.is_prefix_of(i.name)]
        return out

    def should_cancel_solicitation_timer(self) -> bool:
        return len(self._held_interests) == 0


class AutoconfigRepoCore:
    """Autoconfig repository node (registration and forwarder discovery)."""

    def __init__(
        self,
        name: str,
        linklayer: BasicLinkLayer,
        repo: BaseRepository,
        addr: str,
        bcport: int = 9000,
        register_local: bool = True,
        register_global: bool = False,
        logger: Optional[Logger] = None,
    ):
        self._linklayer = linklayer
        self._repository = repo
        self._addr: str = addr
        self._broadcast_port: int = bcport
        self._service_name: str = name
        self._fwd_fid: int = None
        self._register_local: bool = register_local
        self._register_global: bool = register_global
        self._bc_interfaces: List[int] = []
        if self._linklayer is not None:
            for i in range(len(self._linklayer.interfaces)):
                interface = self._linklayer.interfaces[i]
                if interface.get_broadcast_address() is not None and interface.enable_broadcast():
                    self._bc_interfaces.append(i)
        self.logger = logger if logger is not None else Logger("AutoconfigRepoCore", 255)

    def initial_forwarder_solicitations(self) -> List[Outbound]:
        out: List[Outbound] = []
        forwarders_interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)
        for i in self._bc_interfaces:
            interface = self._linklayer.interfaces[i]
            bcaddr: str = interface.get_broadcast_address()
            if bcaddr is not None:
                addr_info = AddressInfo((bcaddr, self._broadcast_port), i)
                autoconf_fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info)
                out.append(Outbound("queue_lower", [autoconf_fid, forwarders_interest]))
        return out

    def handle_from_lower(
        self, fid: int, packet: Packet, addr_info: AddressInfo
    ) -> Tuple[List[Outbound], List[Tuple[Name, AddressInfo, float]]]:
        renewals: List[Tuple[Name, AddressInfo, float]] = []
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            return [Outbound("higher", [fid, packet])], renewals
        if _AUTOCONFIG_FORWARDERS_PREFIX.is_prefix_of(packet.name):
            return self._handle_forwarders(packet, addr_info), renewals
        if _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX.is_prefix_of(packet.name):
            out, renewal = self._handle_service_registration(packet, addr_info)
            if renewal is not None:
                renewals.append(renewal)
            return out, renewals
        return [], renewals

    def handle_from_higher(self, data) -> List[Outbound]:
        return [Outbound("lower", data)]

    def send_service_registration(self, name: Name, addr_info: AddressInfo) -> List[Outbound]:
        if self._fwd_fid is None:
            return []
        interface = self._linklayer.interfaces[addr_info.interface_id]
        if not isinstance(interface, UDP4Interface):
            return []
        interface: UDP4Interface = interface
        registration_name: Name = _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX
        registration_name += f"udp4://{self._addr}:{interface.get_port()}"
        registration_name += name
        self.logger.info(f"Registering service {registration_name}")
        registration_interest = Interest(registration_name)
        self.logger.info("Sending service registration")
        return [Outbound("queue_lower", [self._fwd_fid, registration_interest])]

    def _handle_forwarders(self, packet: Packet, addr_info: AddressInfo) -> List[Outbound]:
        out: List[Outbound] = []
        if not isinstance(packet, Content):
            return out
        self.logger.info("Received forwarder info")
        if len(packet.content) > 0 and packet.content[0] == 128:
            self.logger.error("This implementation cannot handle the autoconfig binary wire format.")
            return out
        lines: List[str] = packet.content.split("\n")
        scheme, addr = lines[0].split("://", 1)
        if scheme != "udp4":
            self.logger.error(f"Don't know how to handle scheme {scheme} in forwarder advertisement.")
            return out
        host, port = addr.split(":")
        self.logger.info(f"forwarder: {host}:{port}")
        fwd_addr = AddressInfo((host, int(port)), addr_info.interface_id)
        self._fwd_fid = self._linklayer.faceidtable.get_or_create_faceid(fwd_addr)
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            t, n = line.split(":")
            if t == "pl" and self._register_local:
                prefix = Name(n)
                self.logger.info(f"Got local prefix {prefix}, sending registration")
                out.extend(self.send_service_registration(prefix + self._service_name, addr_info))
            if t == "pg" and self._register_global:
                prefix = Name(n)
                self.logger.info(f"Got routed prefix {prefix}, sending registration")
                out.extend(self.send_service_registration(prefix + self._service_name, addr_info))
        return out

    def _handle_service_registration(
        self, packet: Packet, addr_info: AddressInfo
    ) -> Tuple[List[Outbound], Optional[Tuple[Name, AddressInfo, float]]]:
        if isinstance(packet, Nack):
            nack: Nack = packet
            self.logger.error(f"Service registration declined: {nack.reason}")
            return [], None
        if isinstance(packet, Content):
            if packet.content is None:
                self.logger.error("Service Registration ACK without timeout")
                return [], None
            if len(packet.content) > 0 and packet.content[0] == 137:
                self.logger.error("This implementation cannot handle the autoconfig binary wire format.")
                return [], None
            regname = Name(packet.name.components[3:])
            try:
                timeout = int(packet.content)
            except ValueError:
                self.logger.error("Service Registration ACK without timeout")
                return [], None
            self.logger.info(f"Service registration accepted: {regname}")
            self._repository.set_prefix(regname)
            return [], (regname, addr_info, timeout / 2.0)
        return [], None

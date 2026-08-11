"""Shared routing-layer logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Name
from PiCN.Processes.Outbound import Outbound


class RoutingLayerCore:
    """Routing RIB/FIB sync and /routing prefix handling."""

    def __init__(
        self,
        linklayer: BasicLinkLayer,
        peers: List[Tuple[str, int]] = None,
        rib_maxage: timedelta = timedelta(seconds=3600),
        prefix: Name = Name("/routing"),
        logger: Optional[Logger] = None,
    ):
        self._linklayer: BasicLinkLayer = linklayer
        self._prefix: Name = prefix
        self.rib: BaseRoutingInformationBase = None
        self.fib: BaseForwardingInformationBase = None
        self._rib_maxage: timedelta = rib_maxage
        self._peers: List[Tuple[str, int]] = peers if peers is not None else []
        self.logger = logger if logger is not None else Logger("RoutingCore", 255)

    def handle_from_lower(self, data) -> List[Outbound]:
        self.logger.info(f"Received data from lower: {data}")
        if len(data) != 2:
            self.logger.warn("Expects [fid, Packet] from lower")
            return []
        rcv_fid, packet = data
        now = datetime.now(timezone.utc)
        if packet.name == self._prefix:
            if isinstance(packet, Interest):
                self.logger.info("Received routing interest")
                output: str = ""
                for name, fid, dist, timeout in self.rib.entries():
                    if timeout is None:
                        output = f"{output}{name}:{dist}:-1\n"
                    else:
                        output = f"{output}{name}:{dist}:{int((timeout - now).total_seconds())}\n"
                content: Content = Content(self._prefix, output.encode("utf-8"))
                return [Outbound("queue_lower", [rcv_fid, content])]
            if isinstance(packet, Content):
                self.logger.info("Received routing content")
                rib: BaseRoutingInformationBase = self.rib
                lines: List[str] = [line for line in packet.content.split("\n") if len(line) > 0]
                for line in lines:
                    name, dist, timeout = line.rsplit(":", 2)
                    if timeout == "-1":
                        timeout = self._rib_maxage
                    else:
                        timeout = timedelta(seconds=int(timeout))
                    rib.insert(
                        Name(name),
                        rcv_fid,
                        int(dist) + 1,
                        now + min(timeout, self._rib_maxage),
                    )
                return []
        return [Outbound("queue_higher", data)]

    def handle_from_higher(self, data) -> List[Outbound]:
        return [Outbound("queue_lower", data)]

    def ageing_and_solicit(self) -> List[Outbound]:
        if self.rib is not None:
            self.rib.ageing()
            self.fib.clear()
            for entry in self.rib.build_fib():
                self.fib.add_fib_entry(entry.name, [entry.faceid], static=entry.static)
        return self.routing_interest_outbounds()

    def routing_interest_outbounds(self) -> List[Outbound]:
        out: List[Outbound] = []
        solicitation: Interest = Interest(self._prefix)
        for addr in self._peers:
            addr_info: AddressInfo = AddressInfo(addr, 0)
            fid = self._linklayer.faceidtable.get_or_create_faceid(addr_info)
            out.append(Outbound("queue_lower", [fid, solicitation]))
        return out

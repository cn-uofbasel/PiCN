"""Shared timeout-prevention / R2C logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects. Directions:
- ``\"lower\"`` / ``\"higher\"`` -- the handler's ``to_lower`` / ``to_higher`` args
- ``\"queue_lower\"`` / ``\"queue_higher\"`` -- the layer's instance queues
  (``self.queue_to_lower`` / ``self.queue_to_higher``), matching observed sync
  code that sometimes puts on the instance queue rather than the handler argument.
"""

import time
from typing import Dict, List, Optional

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.NFNLayer.NFNComputationTable import BaseNFNComputationTable
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Nack, NackReason, Name
from PiCN.Processes.Outbound import Outbound


class TimeoutPreventionMessageDict(object):
    """Datastructure, that contains R2C messages and the matching handlers"""

    def __init__(self):
        self.container: Dict[Name, TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry] = {}

    class TimeoutPreventionMessageDictEntry(object):
        """Datastructure Entry"""

        def __init__(self, packetid):
            self.timestamp = time.time()
            self.packetid = packetid

    def get_entry(self, name: Name) -> TimeoutPreventionMessageDictEntry:
        """search for an entry in the Dict
        :param name: name of the entry
        :return entry if found, else None
        """
        if name in self.container:
            return self.container.get(name)

    def add_entry(self, name: Name, entry: TimeoutPreventionMessageDictEntry):
        """add an entry to the dict
        :param name: Name of the Entry
        :param entry: the entry itself
        """
        self.container[name] = entry

    def create_entry(self, name: Name, packet_id: int):
        """create an new entry given a name
        :param name: name for the entry
        """
        entry = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(packet_id)
        self.add_entry(name, entry)

    def update_timestamp(self, name: Name):
        """set the timestamp of the corresponding entry to time.time()
        :param name: Name of the Entry to be updated
        """
        entry = self.container.get(name)
        if entry is not None:
            self.remove_entry(name)
        else:
            return
        entry_n = TimeoutPreventionMessageDict.TimeoutPreventionMessageDictEntry(entry.packetid)
        self.add_entry(name, entry_n)

    def remove_entry(self, name):
        """Remove an entry from the dict
        :param name: name of the entry to be removed
        """
        if name in self.container:
            del self.container[name]

    def get_container(self):
        return self.container


class TimeoutPreventionCore:
    """KEEPALIVE / R2C timeout prevention shared by sync and async wrappers."""

    def __init__(
        self,
        message_dict: TimeoutPreventionMessageDict,
        nfn_comp_table: BaseNFNComputationTable,
        pit: BasePendingInterestTable = None,
        logger: Optional[Logger] = None,
        timeout_interval: int = 2,
        ageing_interval: int = 1,
    ):
        self.timeout_interval = timeout_interval
        self.ageing_interval = ageing_interval
        self.message_dict = message_dict
        self.computation_table = nfn_comp_table
        # Required because computation table does not sync fast enough.
        self.running_computations: List[Name] = []
        self.pit = pit
        self.logger = logger if logger is not None else Logger("TimeoutPrevCore", 255)

    def handle_from_lower(self, data) -> List[Outbound]:
        out: List[Outbound] = []
        packet_id = data[0]
        packet = data[1]
        if "THUNK" in str(packet.name):
            out.append(Outbound("queue_higher", data))
            return out
        if isinstance(packet, Interest):
            self.logger.info("Reveived Interest from lower... " + str(packet.name))
            if len(packet.name.components) > 2 and packet.name.string_components[-2] == "KEEPALIVE":
                self.logger.info("Interest is keep alive")
                if self.computation_table is None:
                    return out
                nfn_name = self.remove_keep_alive_from_name(packet.name)
                self.logger.info("NFN name is: " + str(nfn_name))
                self.logger.info(
                    "#Running Computations: " + str(self.computation_table.is_comp_running(nfn_name))
                )
                comp = self.computation_table.get_computation(nfn_name)
                if (
                    comp is not None
                    or self.computation_table.is_comp_running(nfn_name)
                    or nfn_name in self.running_computations
                ):
                    out.append(Outbound("lower", [packet_id, Content(packet.name)]))
                else:
                    out.append(
                        Outbound(
                            "lower",
                            [
                                packet_id,
                                Nack(packet.name, NackReason.COMP_NOT_RUNNING, interest=packet),
                            ],
                        )
                    )
                return out
            if len(packet.name.components) > 0 and packet.name.components[-1] == b"NFN":
                self.running_computations.append(packet.name)
                out.append(Outbound("higher", data))
            else:
                out.append(Outbound("higher", data))
        elif (
            (isinstance(packet, Content) or isinstance(packet, Nack))
            and len(packet.name.components) > 2
            and packet.name.string_components[-2] == "KEEPALIVE"
        ):
            if isinstance(packet, Content):
                self.logger.info("Received KEEP ALIVE reply, updating timestamps")
                entry = self.message_dict.get_entry(packet.name)
                if entry:
                    self.logger.info("Old Timestamp was: " + str(entry.timestamp))
                    self.message_dict.update_timestamp(packet.name)
                    updated = self.message_dict.get_entry(packet.name)
                    if updated:
                        self.logger.info("Timestamp is now: " + str(updated.timestamp))
                return out
            if isinstance(packet, Nack):
                original_name = self.remove_keep_alive_from_name(packet.name)
                self.message_dict.remove_entry(packet.name)
                self.message_dict.remove_entry(original_name)
                out.append(
                    Outbound(
                        "queue_higher",
                        [
                            packet_id,
                            Nack(
                                original_name,
                                reason=NackReason.COMP_NOT_RUNNING,
                                interest=Interest(original_name),
                            ),
                        ],
                    )
                )
        elif isinstance(packet, Content) or isinstance(packet, Nack):
            entry = self.message_dict.get_entry(packet.name)
            if entry is not None:
                self.logger.info("Removing entry from Keep Alive Dict")
                self.message_dict.remove_entry(packet.name)
                keepalive_name = self.add_keep_alive_from_name(packet.name)
                self.message_dict.remove_entry(keepalive_name)
            out.append(Outbound("higher", data))
        return out

    def handle_from_higher(self, data) -> List[Outbound]:
        out: List[Outbound] = []
        packet_id = data[0]
        packet = data[1]
        if "THUNK" in str(packet.name):
            out.append(Outbound("queue_lower", data))
            return out
        if (isinstance(packet, Content) or isinstance(packet, Nack)) and packet.name in self.running_computations:
            self.running_computations.remove(packet.name)
            self.message_dict.remove_entry(packet.name)
        self.logger.info("Received Packet from higher")
        if isinstance(packet, Interest):
            self.logger.info("Packet is NFN interest, start timeout prevention")
            keepalive_name = self.add_keep_alive_from_name(packet.name)
            self.message_dict.create_entry(name=packet.name, packet_id=packet_id)
            self.message_dict.create_entry(name=keepalive_name, packet_id=packet_id)
        out.append(Outbound("lower", data))
        return out

    def ageing(self) -> List[Outbound]:
        """Age message dict; return retransmits and timeout Nacks. Does not schedule a timer."""
        out: List[Outbound] = []
        timestamp = time.time()
        try:
            removes = []
            container = self.message_dict.get_container()
            for name in container:
                entry = self.message_dict.get_entry(name)
                if len(name.components) > 2 and name.string_components[-2] == "KEEPALIVE":
                    if entry.timestamp + self.timeout_interval < timestamp:
                        self.logger.info(
                            "Remove Keep Alvie Job because of timeout. Timestamp is: "
                            + str(entry.timestamp)
                            + " Now is: "
                            + str(timestamp)
                        )
                        removes.append(name)
                        if name in self.running_computations:
                            self.running_computations.remove(name)
                        original_name = self.remove_keep_alive_from_name(name)
                        removes.append(original_name)
                        if original_name in self.running_computations:
                            self.running_computations.remove(original_name)
                        nack = Nack(
                            name=original_name,
                            reason=NackReason.COMP_NOT_RUNNING,
                            interest=Interest(name),
                        )
                        out.append(Outbound("queue_higher", [entry.packetid, nack]))
                    else:
                        out.append(Outbound("queue_lower", [entry.packetid, Interest(name=name)]))
                else:
                    if name.components[-1] != b"NFN" and entry.timestamp + self.timeout_interval < time.time():
                        removes.append(name)
                        nack = Nack(
                            name=name,
                            reason=NackReason.COMP_PARAM_UNAVAILABLE,
                            interest=Interest(name),
                        )
                        out.append(Outbound("queue_higher", [entry.packetid, nack]))
                    else:
                        out.append(Outbound("queue_lower", [entry.packetid, Interest(name=name)]))
            for n in removes:
                self.message_dict.remove_entry(n)
                if self.pit is not None:
                    self.pit.remove_pit_entry(n)
        except Exception as e:
            self.logger.warning("Exception during ageing: " + str(e))
        return out

    def add_keep_alive_from_name(self, name: Name) -> Name:
        if name.components[-1] != b"NFN":
            return name
        new_name = Name()
        for n in name.string_components:
            new_name += n
        new_name.components.remove(b"NFN")
        new_name += "KEEPALIVE"
        new_name += "NFN"
        return new_name

    def remove_keep_alive_from_name(self, name: Name) -> Name:
        if name.components[-1] != b"NFN":
            return name
        new_name = Name()
        for n in name.string_components:
            new_name += n
        new_name.components.remove(b"KEEPALIVE")
        return new_name

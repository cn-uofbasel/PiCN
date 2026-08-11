"""Shared chunking / reassembly logic (ADR-003 extract-core).

Returns ``List[Outbound]``; does not touch queue objects.
"""

import time
from typing import Dict, List, Optional, Tuple

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer, SimpleContentChunkifyer
from PiCN.Logger import Logger
from PiCN.Packets import Content, Interest, Name, Nack
from PiCN.Processes.Outbound import Outbound


class RequestTableEntry(object):
    """Request table for Pending chunks"""

    def __init__(self, name: Name):
        self.name: Name = name
        self.requested_chunks = []
        self.chunks = []
        self.requested_md = []
        self.chunked = False
        self.lastchunk: Name

    def __eq__(self, other):
        return self.name == other.name


class ChunkLayerCore:
    """Chunking logic shared by sync and async wrappers."""

    def __init__(self, chunkifyer: BaseChunkifyer = None, chunk_size: int = 4096,
                 chunk_table: Optional[Dict] = None, request_table: Optional[List] = None,
                 logger: Optional[Logger] = None):
        self.chunk_size = chunk_size
        if chunkifyer is None:
            self.chunkifyer = SimpleContentChunkifyer(chunk_size)
        else:
            self.chunkifyer: BaseChunkifyer = chunkifyer
        self._chunk_table: Dict[Name, Tuple[Content, float]] = (
            chunk_table if chunk_table is not None else {}
        )
        self._request_table: List[RequestTableEntry] = (
            request_table if request_table is not None else []
        )
        self.logger = logger if logger is not None else Logger("ChunkCore", 255)

    def handle_from_higher(self, data) -> List[Outbound]:
        self.logger.info("Got Data from higher")
        faceid = data[0]
        packet = data[1]
        out: List[Outbound] = []
        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest " + str(packet.name))
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is None:
                self._request_table.append(RequestTableEntry(packet.name))
            out.append(Outbound("lower", [faceid, packet]))
            return out
        if isinstance(packet, Content):
            self.logger.info("Packet is Content (name=%s, %d bytes)" % (
                str(packet.name), len(packet.content)))
            if len(packet.content) < self.chunk_size:
                out.append(Outbound("lower", [faceid, packet]))
            else:
                self.logger.info("Chunking Packet")
                metadata, chunks = self.chunkifyer.chunk_data(packet)
                self.logger.info("Metadata: " + metadata[0].content)
                out.append(Outbound("lower", [faceid, metadata[0]]))
                for md in metadata:
                    if md.name not in self._chunk_table:
                        self._chunk_table[md.name] = (md, time.time())
                for c in chunks:
                    if c.name not in self._chunk_table:
                        self._chunk_table[c.name] = (c, time.time())
            return out
        if isinstance(packet, Nack):
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is not None:
                self._request_table.remove(requestentry)
            out.append(Outbound("lower", [faceid, packet]))
        return out

    def handle_from_lower(self, data) -> List[Outbound]:
        self.logger.info("Got Data from lower")
        faceid = data[0]
        packet = data[1]
        out: List[Outbound] = []
        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest")
            if packet.name in self._chunk_table:
                matching_content = self._chunk_table.get(packet.name)[0]
                out.append(Outbound("lower", [faceid, matching_content]))
            else:
                out.append(Outbound("higher", [faceid, packet]))
            return out
        if isinstance(packet, Content):
            self.logger.info("Packet is Content")
            request_table_entry = self.get_request_table_entry(packet.name)
            if request_table_entry is None:
                return out
            self._request_table.remove(request_table_entry)
            if request_table_entry.chunked is False:
                if not packet.get_bytes().startswith(b'mdo:'):
                    out.append(Outbound("higher", [faceid, packet]))
                    return out
                request_table_entry.chunked = True
            if packet.get_bytes().startswith(b'mdo:'):
                request_table_entry, meta_out = self.handle_received_meta_data(
                    faceid, packet, request_table_entry)
                out.extend(meta_out)
            else:
                request_table_entry, chunk_out = self.handle_received_chunk_data(
                    faceid, packet, request_table_entry)
                out.extend(chunk_out)
                if request_table_entry is None:
                    return out
            self._request_table.append(request_table_entry)
            return out
        if isinstance(packet, Nack):
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is not None:
                self._request_table.remove(requestentry)
            out.append(Outbound("higher", [faceid, packet]))
        return out

    def handle_received_meta_data(self, faceid: int, packet: Content,
                                  request_table_entry: RequestTableEntry) -> Tuple[RequestTableEntry, List[Outbound]]:
        """Handle the case, where metadata are received from the network"""
        out: List[Outbound] = []
        md_entry = self.metadata_name_in_request_table(packet.name)
        if md_entry is None:
            return request_table_entry, out
        request_table_entry = self.remove_metadata_name_from_request_table(
            request_table_entry, packet.name)
        md, chunks, size = self.chunkifyer.parse_meta_data(packet.content)
        if md is not None:
            request_table_entry.requested_md.append(md)
            out.append(Outbound("lower", [faceid, Interest(md)]))
        else:
            request_table_entry.lastchunk = chunks[-1]
        for chunk in chunks:
            request_table_entry.requested_chunks.append(chunk)
            out.append(Outbound("lower", [faceid, Interest(chunk)]))
        self._chunk_table[packet.name] = (packet, time.time())
        return request_table_entry, out

    def handle_received_chunk_data(self, faceid: int, packet: Content,
                                   request_table_entry: RequestTableEntry) -> Tuple[
            Optional[RequestTableEntry], List[Outbound]]:
        """Handle the case wehere chunk data are received """
        out: List[Outbound] = []
        chunk_entry = self.chunk_name_in_request_table(packet.name)
        if chunk_entry is None:
            return request_table_entry, out
        request_table_entry.chunks.append(packet)
        request_table_entry = self.remove_chunk_name_from_request_table_entry(
            request_table_entry, packet.name)
        self._chunk_table[packet.name] = (packet, time.time())
        if request_table_entry.chunked and len(request_table_entry.requested_chunks) == 0 \
                and len(request_table_entry.requested_md) == 0:
            data = request_table_entry.chunks
            data = sorted(data,
                          key=lambda content: int(''.join(filter(str.isdigit, content.name.string_components[-1]))))
            cont = self.chunkifyer.reassamble_data(request_table_entry.name, data)
            out.append(Outbound("higher", [faceid, cont]))
            return None, out
        return request_table_entry, out

    def get_chunk_list_from_chunk_table(self, data_names: Name) -> List[Content]:
        """get a list of content objects from a list of names"""
        res = []
        for name in data_names:
            if name in self._chunk_table:
                res.append(self._chunk_table[name][0])
        return res

    def get_request_table_entry(self, name: Name) -> RequestTableEntry:
        """check if a name is in the chunktable"""
        for entry in self._request_table:
            if entry.name == name or name in entry.requested_chunks or name in entry.requested_md:
                return entry
        return None

    def chunk_name_in_request_table(self, name):
        """check if a received chunk is expected by the requesttable"""
        for entry in self._request_table:
            if name in entry.requested_chunks:
                return True
        return False

    def remove_chunk_name_from_request_table_entry(self, request_table_entry: RequestTableEntry, name: Name) \
            -> RequestTableEntry:
        """remove chunk from chunktable"""
        if name not in request_table_entry.requested_chunks:
            return request_table_entry
        request_table_entry.requested_chunks.remove(name)
        return request_table_entry

    def metadata_name_in_request_table(self, name):
        """check if a received metadata is expected by the chunktable"""
        for entry in self._request_table:
            if name in entry.requested_md:
                return True
        return False

    def remove_metadata_name_from_request_table(self, request_table_entry: RequestTableEntry, name: Name) \
            -> RequestTableEntry:
        """remove metadata from chunktable"""
        if name not in request_table_entry.requested_md:
            return request_table_entry
        request_table_entry.requested_md.remove(name)
        return request_table_entry

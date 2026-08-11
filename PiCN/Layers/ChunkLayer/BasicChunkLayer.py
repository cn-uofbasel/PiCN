""""Basic Chunking Layer for PICN"""

import multiprocessing

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer
from PiCN.Layers.ChunkLayer.ChunkLayerCore import ChunkLayerCore, RequestTableEntry
from PiCN.Packets import Content
from PiCN.Processes import LayerProcess
from PiCN.Processes.Outbound import Outbound

__all__ = ["BasicChunkLayer", "RequestTableEntry"]


class BasicChunkLayer(LayerProcess):
    """"Basic Chunking Layer for PICN

    Thin sync wrapper around :class:`ChunkLayerCore` (ADR-003 extract-core).
    """

    def __init__(self, chunkifyer: BaseChunkifyer = None, chunk_size: int = 4096,
                 manager: multiprocessing.Manager = None, log_level=255):
        super().__init__("ChunkLayer", log_level=log_level)
        if manager is None:
            manager = multiprocessing.Manager()
        chunk_table = manager.dict()
        request_table = manager.list()
        self._core = ChunkLayerCore(
            chunkifyer=chunkifyer, chunk_size=chunk_size,
            chunk_table=chunk_table, request_table=request_table, logger=self.logger)

    @property
    def chunk_size(self):
        return self._core.chunk_size

    @property
    def chunkifyer(self):
        return self._core.chunkifyer

    @property
    def _chunk_table(self):
        return self._core._chunk_table

    @property
    def _request_table(self):
        return self._core._request_table

    def _apply_outbound(self, out: Outbound, to_lower, to_higher) -> None:
        if out.direction == "lower":
            to_lower.put(out.item)
        elif out.direction == "higher":
            to_higher.put(out.item)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_higher(data):
            self._apply_outbound(out, to_lower, to_higher)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        for out in self._core.handle_from_lower(data):
            self._apply_outbound(out, to_lower, to_higher)

    def handle_received_meta_data(self, faceid: int, packet: Content, request_table_entry: RequestTableEntry,
                                  to_lower: multiprocessing.Queue) -> RequestTableEntry:
        """Handle the case, where metadata are received from the network"""
        request_table_entry, outs = self._core.handle_received_meta_data(
            faceid, packet, request_table_entry)
        for out in outs:
            to_lower.put(out.item)
        return request_table_entry

    def handle_received_chunk_data(self, faceid: int, packet: Content, request_table_entry: RequestTableEntry,
                                   to_higher: multiprocessing.Queue) -> RequestTableEntry:
        """Handle the case wehere chunk data are received """
        request_table_entry, outs = self._core.handle_received_chunk_data(
            faceid, packet, request_table_entry)
        for out in outs:
            to_higher.put(out.item)
        return request_table_entry

    def get_chunk_list_from_chunk_table(self, data_names):
        return self._core.get_chunk_list_from_chunk_table(data_names)

    def get_request_table_entry(self, name):
        return self._core.get_request_table_entry(name)

    def chunk_name_in_request_table(self, name):
        return self._core.chunk_name_in_request_table(name)

    def remove_chunk_name_from_request_table_entry(self, request_table_entry, name):
        return self._core.remove_chunk_name_from_request_table_entry(request_table_entry, name)

    def metadata_name_in_request_table(self, name):
        return self._core.metadata_name_in_request_table(name)

    def remove_metadata_name_from_request_table(self, request_table_entry, name):
        return self._core.remove_metadata_name_from_request_table(request_table_entry, name)

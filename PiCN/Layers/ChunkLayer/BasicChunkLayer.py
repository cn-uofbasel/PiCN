""""Basic Chunking Layer for PICN"""

import multiprocessing
import time
from typing import Dict, List

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer, SimpleContentChunkifyer
from PiCN.Packets import Content, Interest, Name, Nack
from PiCN.Processes import LayerProcess


class RequestTableEntry(object):
    """Request table for Pending chunks"""

    def __init__(self, name: Name):
        self.name: Name = name
        self.requested_chunks = []
        self.chunks =[]
        self.requested_md = []
        self.chunked = False
        self.lastchunk:Name

    def __eq__(self, other):
        return self.name == other.name

class BasicChunkLayer(LayerProcess):
    """"Basic Chunking Layer for PICN"""

    def __init__(self, chunkifyer: BaseChunkifyer=None, chunk_size: int=4096, manager: multiprocessing.Manager=None,
                 log_level=255):
        super().__init__("ChunkLayer", log_level=log_level)
        self.chunk_size = chunk_size
        if chunkifyer == None:
            self.chunkifyer = SimpleContentChunkifyer(chunk_size)
        else:
            self.chunkifyer: BaseChunkifyer = chunkifyer
        if manager is None:
            manager = multiprocessing.Manager()
        self._chunk_table: Dict[Name, (Content, float)] = manager.dict()
        self._request_table: List[RequestTableEntry] = manager.list()

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from higher")
        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest " + str(packet.name))
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is None:
                self._request_table.append(RequestTableEntry(packet.name))
            to_lower.put([faceid, packet])
            return
        if isinstance(packet, Content):
            self.logger.info("Packet is Content (name=%s, %d bytes)" % \
                                      (str(packet.name), len(packet.content)))
            if len(packet.content) < self.chunk_size:
                to_lower.put([faceid, packet])
            else:
                self.logger.info("Chunking Packet")
                metadata, chunks = self.chunkifyer.chunk_data(packet) #create metadata and chunks
                self.logger.info("Metadata: " + metadata[0].content)
                to_lower.put([faceid, metadata[0]]) #return first name TODO HANDLE THE CASE, WHERE CHUNKS CAN TIMEOUT AND MUST BE REPRODUCED
                for md in metadata: #add metadata to chunktable
                    if md.name not in self._chunk_table:
                        self._chunk_table[md.name] = (md, time.time())
                for c in chunks: #add chunks to chunktable
                    if c.name not in self._chunk_table:
                        self._chunk_table[c.name] = (c, time.time())
        if isinstance(packet, Nack):
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is not None:
                self._request_table.remove(requestentry)
            to_lower.put([faceid, packet])

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from lower")
        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest")
            if packet.name in self._chunk_table: #Check if Interest is in chunktable
                matching_content = self._chunk_table.get(packet.name)[0]
                to_lower.put([faceid, matching_content])
            else:
                to_higher.put([faceid, packet])
            return
        if isinstance(packet, Content):
            self.logger.info("Packet is Content")
            request_table_entry = self.get_request_table_entry(packet.name)
            if request_table_entry is None:
                return
            self._request_table.remove(request_table_entry)
            if request_table_entry.chunked is False: #not chunked content
                if not packet.get_bytes().startswith(b'mdo:'):
                    to_higher.put([faceid, packet])
                    return
                else: # Received metadata data --> chunked content
                    request_table_entry.chunked = True
            if packet.get_bytes().startswith(b'mdo:'): # request all frames from metadata
                request_table_entry = self.handle_received_meta_data(faceid, packet, request_table_entry, to_lower)
            else:
                request_table_entry = self.handle_received_chunk_data(faceid, packet, request_table_entry, to_higher)
                if request_table_entry is None:
                    return #deletes entry if data was completed
            self._request_table.append(request_table_entry)
        if isinstance(packet, Nack):
            requestentry = self.get_request_table_entry(packet.name)
            if requestentry is not None:
                self._request_table.remove(requestentry)
            to_higher.put([faceid, packet])

    def handle_received_meta_data(self, faceid: int, packet: Content, request_table_entry: RequestTableEntry,
                                  to_lower: multiprocessing.Queue) -> RequestTableEntry:
        """Handle the case, where metadata are received from the network"""
        md_entry = self.metadata_name_in_request_table(packet.name)
        if md_entry is None:
            return request_table_entry
        request_table_entry = self.remove_metadata_name_from_request_table(request_table_entry, packet.name)
        md, chunks = self.chunkifyer.parse_meta_data(packet.content)
        if md is not None:  # there is another md file
            request_table_entry.requested_md.append(md)
            to_lower.put([faceid, Interest(md)])
        else:
            request_table_entry.lastchunk = chunks[-1]
        for chunk in chunks:  # request all chunks from the metadata file
            request_table_entry.requested_chunks.append(chunk)
            to_lower.put([faceid, Interest(chunk)])
        self._chunk_table[packet.name] = (packet, time.time())
        return request_table_entry

    def handle_received_chunk_data(self, faceid: int, packet: Content, request_table_entry: RequestTableEntry,
                                   to_higher: multiprocessing.Queue) -> RequestTableEntry:
        """Handle the case wehere chunk data are received """
        chunk_entry = self.chunk_name_in_request_table(packet.name)
        if chunk_entry is None:
            return request_table_entry
        request_table_entry.chunks.append(packet)
        request_table_entry = self.remove_chunk_name_from_request_table_entry(request_table_entry, packet.name)
        self._chunk_table[packet.name] = (packet, time.time())
        if request_table_entry.chunked and len(request_table_entry.requested_chunks) == 0 \
                and len(request_table_entry.requested_md) == 0:  # all chunks are available
            data = request_table_entry.chunks
            data = sorted(data, key=lambda content: content.name.to_string())
            cont = self.chunkifyer.reassamble_data(request_table_entry.name, data)
            to_higher.put([faceid, cont])
            return None
        else:
            return request_table_entry

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

    def remove_chunk_name_from_request_table_entry(self, request_table_entry: RequestTableEntry, name: Name)\
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

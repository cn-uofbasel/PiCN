""""
Chunking Layer for PICN handling interrupted data uploads by using available data from neighbouring nodes.

This implementation always first asks the neighbouring nodes for the requested data.
As soon as two NACKS are received (-> no more data available from neighbours), the rest of the files get
requested from the original source.
"""

import multiprocessing
import time
from typing import Dict, List

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer, SimpleContentChunkifyer
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Packets import Content, Interest, Name, Nack, Packet, NackReason
from PiCN.Processes import LayerProcess


class RequestTableEntry(object):
    """Request table entry for pending chunks"""

    def __init__(self, name: Name):
        self.name: Name = name
        self.requested_chunks = []
        self.chunks =[]
        self.requested_md = []
        self.chunked = False
        self.last_chunk: Name

    def __eq__(self, other):
        return self.name == other.name

class ClEntry(object):
    """CL table entry"""

    def __init__(self, interest):
        self.nack_L = True
        self.nack_R = True
        self.interest = interest
        self.interest_requested = False
        self.recipient = None

class DataOffloadingChunklayerSimple(LayerProcess):
    """This Chunklayer handles interrupted data uploads by asking neighbouring nodes for available content."""

    def __init__(self, cs: BaseContentStore, pit: BasePendingInterestTable, fib: BaseForwardingInformationBase,
                 chunkifyer: BaseChunkifyer=None, chunk_size: int=4096, num_of_forwards: int=1, prefix: str="car",
                 log_level: int=255):
        super().__init__("ChunkLayer", log_level=log_level)
        self.cs = cs
        self.pit = pit
        self.fib = fib
        self.chunk_size = chunk_size
        if chunkifyer is None:
            self.chunkifyer = SimpleContentChunkifyer(chunk_size)
        else:
            self.chunkifyer: BaseChunkifyer = chunkifyer
        self.num_of_forwards = num_of_forwards
        self.prefix = prefix

        manager = multiprocessing.Manager()
        self._chunk_table: Dict[Name, (Content, float)] = manager.dict()
        self._request_table: List[RequestTableEntry] = manager.list()
        self._cl_table: Dict[Name, ClEntry] = manager.dict()

        self.pass_through = False
        self.cl_sent = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from higher")
        faceid = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest " + str(packet.name))
            request_entry = self.get_request_entry(packet.name)
            if request_entry is None:
                self._request_table.append(RequestTableEntry(packet.name))

            # If the interest starts with "/car" and not ends with "NFN", request metadata and available chunks from neighbours
            components = packet.name.string_components
            if self.prefix in components[0] and components[-1] != "NFN" and not request_entry:
                self.pass_through = False
                self._cl_table[packet.name] = ClEntry(data)
                cl_entry = self._cl_table.get(packet.name)

                name1 = Name("/nL") + packet.name + f"CL{self.num_of_forwards}"
                name2 = Name("/nR") + packet.name + f"CL{self.num_of_forwards}"
                if not self.pit.find_pit_entry(name1) and self.fib.find_fib_entry(name1):
                    cl_entry.nack_L = False
                    self.cl_sent = True
                    to_lower.put([faceid, Interest(name1)])
                if not self.pit.find_pit_entry(name2) and self.fib.find_fib_entry(name2):
                    cl_entry.nack_R = False
                    self.cl_sent = True
                    to_lower.put([faceid, Interest(name2)])
                if self.cl_sent:
                    self._cl_table[packet.name] = cl_entry
                    return

            to_lower.put(data)
            return

        elif isinstance(packet, Content):
            self.logger.info("Packet is Content (name=%s, %d bytes)" %(str(packet.name), len(packet.content)))
            if len(packet.content) < self.chunk_size:
                to_lower.put(data)
            else:
                self.logger.info("Chunking Packet")
                metadata, chunks = self.chunkifyer.chunk_data(packet)  # Create metadata and chunks
                self.logger.info("Metadata: " + metadata[0].content)
                to_lower.put([faceid, metadata[0]])  # Return name of first metadata object
                for md in metadata:  # Add metadata to chunktable
                    if md.name not in self._chunk_table:
                        self._chunk_table[md.name] = (md, time.time())
                for c in chunks:  # Add chunks to chunktable
                    if c.name not in self._chunk_table:
                        self._chunk_table[c.name] = (c, time.time())

        elif isinstance(packet, Nack):
            request_entry = self.get_request_entry(packet.name)
            if request_entry is not None:
                self._request_table.remove(request_entry)
            to_lower.put(data)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from lower")
        faceid = data[0]
        packet = data[1]
        components = packet.name.components
        string_components = packet.name.string_components
        last = components[-1]

        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest")

            # General Interest passed on to chunklayer
            if "CL" in string_components[-1]:
                matching_content = self.get_matching_content(packet)
                if last == b"CL0" or isinstance(matching_content, Content):   # If there is matching content, return it
                    to_lower.put([faceid, matching_content])
                else:  # Otherwise try to pass on to neighbour
                    to_lower.put([faceid, Interest(self.decrease_name(packet.name))])

            elif packet.name in self._chunk_table:
                matching_content = self._chunk_table.get(packet.name)[0]
                to_lower.put([faceid, matching_content])
            else:
                to_higher.put(data)

        elif isinstance(packet, Content):
            self.logger.info("Packet is Content")
            cl_content = False

            # Content from the chunklayer of a neighbouring node
            if "CL" in string_components[-1]:
                if string_components[-1] == f"CL{self.num_of_forwards}":  # This is the requesting node --> unpack
                    cl_content = True
                    packet.name = self.unpack(packet.name)
                    # Save the sender of this packet as the recipient for further interests. Used in pack_cl()
                    request_entry = self.get_request_entry(packet.name)
                    if request_entry:
                        cl_entry = self._cl_table.get(request_entry.name)
                        if cl_entry.interest_requested: # If we already resent requests to source, don't consider it
                            return
                        cl_entry.recipient = Name(components[:1])
                        self._cl_table[request_entry.name] = cl_entry

                else:  # This is not the requesting node --> pass on to neighbour
                    to_lower.put([faceid, Content(self.increase_name(packet.name), packet.content)])
                    return

            request_entry = self.get_request_entry(packet.name)
            if request_entry is None:
                return
            self.handle_content(faceid, packet, request_entry, cl_content, to_lower, to_higher)

        elif isinstance(packet, Nack):
            if self.prefix not in string_components[0]:
                request_entry = self.get_request_entry(packet.name)
                if request_entry:
                    self._request_table.remove(request_entry)

                if "CL" in string_components[-1]:
                    if string_components[-1] == f"CL{self.num_of_forwards}":  # This is the requesting node --> unpack
                        name_unpacked = self.unpack(packet.name)
                        request_entry = self.get_request_entry(name_unpacked)
                        if request_entry:
                            cl_entry = self._cl_table.get(request_entry.name)
                            if components[0] == b"nL":
                                cl_entry.nack_L = True
                            else:
                                cl_entry.nack_R = True
                            if cl_entry.nack_L and cl_entry.nack_R and not cl_entry.interest_requested:
                                # No more data available from neighbours, get it from car
                                self.get_missing_data_from_original_source(faceid, request_entry, cl_entry, to_lower)

                            self._cl_table[request_entry.name] = cl_entry
                    else:
                        name = self.increase_name(packet.name)
                        nack = Nack(name, NackReason.NO_CONTENT, Interest(name))
                        to_lower.put([faceid, nack])
                else:
                    to_higher.put([faceid, packet])
                self.pit.remove_pit_entry(packet.name)
            else:
                if "c" in string_components[-1] or "m" in string_components[-1]:
                    packet.name.components = components[:-1]
                    to_higher.put([faceid, Nack(packet.name, NackReason.NO_CONTENT, Interest(packet.name))])
                else:
                    pass
                    # to_higher.put([faceid, packet])

    def handle_content(self, faceid: int, packet: Content, request_entry: RequestTableEntry, cl_content: bool,
                       to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """Handle incoming content"""
        self._request_table.remove(request_entry)
        if request_entry.chunked is False:  # Not chunked content
            if not packet.get_bytes().startswith(b'mdo:'):
                to_higher.put([faceid, packet])
                return
            else:  # Received metadata data --> chunked content
                request_entry.chunked = True
        if packet.get_bytes().startswith(b'mdo:'):  # Request all frames from metadata
            self.handle_received_meta_data(faceid, packet, request_entry, to_lower, cl_content)
        else:
            self.handle_received_chunk_data(faceid, packet, request_entry, to_higher)

    def handle_received_meta_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                  to_lower: multiprocessing.Queue, cl_content: bool):
        """Handle meta data"""
        if packet.name in request_entry.requested_md:
            request_entry.requested_md.remove(packet.name)
        md, chunks, size = self.chunkifyer.parse_meta_data(packet.content)
        for chunk in chunks:  # Request all chunks from the metadata file if not already received or requested
            # if chunk not in request_entry.requested_chunks and chunk not in [i.name for i in request_entry.chunks]:
            if chunk not in [i.name for i in request_entry.chunks]:
                request_entry.requested_chunks.append(chunk)
                if not self.pass_through:
                    if cl_content:
                        cl_entry = self._cl_table.get(request_entry.name)
                        if cl_entry.nack_L and cl_entry.nack_R:
                            break
                        chunk = self.pack_cl(chunk)
                    to_lower.put([faceid, Interest(chunk)])
        if md is not None:  # There is another md file
            if md not in request_entry.requested_md:
                request_entry.requested_md.append(md)
            if not self.pass_through:
                if cl_content:
                    cl_entry = self._cl_table.get(request_entry.name)
                    if not (cl_entry.nack_L and cl_entry.nack_R):
                        cl_entry.interest = [faceid, Interest(packet.name)]
                        self._cl_table[request_entry.name] = cl_entry
                        md = self.pack_cl(md)
                        to_lower.put([faceid, Interest(md)])
                else:
                    to_lower.put([faceid, Interest(md)])
        else:
            request_entry.last_chunk = chunks[-1]
        self._chunk_table[packet.name] = (packet, time.time())
        self._request_table.append(request_entry)

    def handle_received_chunk_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                   to_higher: multiprocessing.Queue):
        """Handle chunk data"""
        if packet.name in request_entry.requested_chunks:
            request_entry.requested_chunks.remove(packet.name)
            request_entry.chunks.append(packet)
        self._chunk_table[packet.name] = (packet, time.time())
        if not request_entry.requested_chunks and not request_entry.requested_md:
            if not request_entry.requested_md:  # All chunks are available
                data = request_entry.chunks
                data = sorted(data, key=lambda content: int(''.join(filter(str.isdigit, content.name.string_components[-1]))))
                cont = self.chunkifyer.reassamble_data(request_entry.name, data)
                to_higher.put([faceid, cont])
                return

        self._request_table.append(request_entry)

    def get_request_entry(self, name: Name):
        """
        Check if a name is in the request table.
        Return entry or None.
        """
        for entry in self._request_table:
            if entry.name == name or name in entry.requested_chunks or name in entry.requested_md:
                return entry
        return None

    def get_matching_content(self, packet: Packet):
        """Return either the content matching the packet name or NACK"""
        name_in = self.unpack(packet.name)
        cs_entry = self.cs.find_content_object(name_in)
        if name_in in self._chunk_table:
            matching_content = self._chunk_table.get(name_in)[0]
            matching_content.name = packet.name
            return matching_content
        elif cs_entry:
            matching_content = cs_entry.content
            matching_content.name = packet.name
            return matching_content
        else:
            return Nack(packet.name, NackReason.NO_CONTENT, packet)

    def pack_cl(self, name: Name) -> Name:
        """Prepend the recipient, append "CL" and the number of forwards."""
        lookup_name = Name(name.components[:-1])
        return self._cl_table.get(lookup_name).recipient + name + f"CL{self.num_of_forwards}"

    def unpack(self, name: Name) -> Name:
        return Name(name.components[1:-1])

    def increase_name(self, name: Name) -> Name:
        """
        Increase the number at the end of the name.
        The number is used to determine whether or not a packet gets forwarded to the next neighbour.
        """
        components = name.components
        last = components[-1].decode("utf-8")
        i = int(''.join(filter(str.isdigit, last)))
        if "CL" in last:
            return Name(components[:-1]) + f"CL{i+1}"
        return name

    def decrease_name(self, name: Name) -> Name:
        """
        Decrease the number at the end of the name.
        The number is used to determine whether or not a packet gets forwarded to the next neighbour.
        """
        components = name.components
        last = components[-1].decode("utf-8")
        i = int(''.join(filter(str.isdigit, last)))
        if "CL" in last:
            return Name(components[:-1]) + f"CL{i-1}"
        return name

    def get_missing_data_from_original_source(self, faceid: int, request_entry: RequestTableEntry, cl_entry: ClEntry,
                                              to_lower: multiprocessing.Queue):
        """
        Start requesting the missing files from the original source.
        """
        if not cl_entry.interest_requested:
            if request_entry.requested_chunks:
                # Request again all chunks that have been requested but not satisfied yet
                for chunk in request_entry.requested_chunks:
                    to_lower.put([faceid, Interest(chunk)])

            # If requested_md is not empty, request them again from source
            if request_entry.requested_md:
                for md in request_entry.requested_md:
                    to_lower.put([faceid, Interest(md)])
            else:  # if empty, request orginal interest from source
                self._request_table.remove(request_entry)
                request_entry.requested_md.append(cl_entry.interest[1].name)
                self._request_table.append(request_entry)
                to_lower.put(cl_entry.interest)
            cl_entry.interest_requested = True

    def set_number_of_forwards(self, number_of_forwards: int):
        self.num_of_forwards = number_of_forwards
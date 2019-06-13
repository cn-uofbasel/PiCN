""""
Chunking Layer for PICN handling interrupted data uploads by using available content from neighbouring nodes.


This implementation sends a special CA interest to its neighbouring nodes. The response is either a list of available
chunks, or a NACK. These chunks are then requested from the corresponding neighbour, while the rest of the interests are
sent to the original source.
"""

import multiprocessing
import time
from typing import Dict, List
import math

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

    def __eq__(self, other):
        return self.name == other.name


class CaEntry(object):
    """CA table entry"""

    def __init__(self):
        self.answer_L = True
        self.answer_R = True
        self.received_all = False
        self.recipient = None
        self.size = 0
        self.ca = None
        self.completely_available = False


class DataOffloadingChunklayer(LayerProcess):
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
        self._ca_table: Dict[Name, CaEntry] = manager.dict()
        self.recipient_cl: Dict[Name, Name] = manager.dict()
        self.pass_through = False

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from higher")
        faceid = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest " + str(packet.name))
            request_entry = self.get_request_entry(packet.name)
            if request_entry is None:
                self._request_table.append(RequestTableEntry(packet.name))
                self._ca_table[packet.name] = CaEntry()

            # If the interest starts with /car and not ends with NFN, request metadata and available chunks from neighbours
            components = packet.name.string_components
            if self.prefix in components[0] and components[-1] != "NFN" and not request_entry:
                self.pass_through = False
                ca_entry = self._ca_table.get(packet.name)
                name1 = Name("/nL") + packet.name + f"CA{self.num_of_forwards}"
                name2 = Name("/nR") + packet.name + f"CA{self.num_of_forwards}"
                name3 = Name("/nL") + packet.name + f"CL{self.num_of_forwards}"
                name4 = Name("/nR") + packet.name + f"CL{self.num_of_forwards}"
                if not self.pit.find_pit_entry(name1) and self.fib.find_fib_entry(name1):
                    ca_entry.answer_L = False
                    ca_entry.received_all = False
                    to_lower.put([faceid, Interest(name1)])
                if not self.pit.find_pit_entry(name2) and self.fib.find_fib_entry(name2):
                    ca_entry.answer_R = False
                    ca_entry.received_all = False
                    to_lower.put([faceid, Interest(name2)])
                if not self.pit.find_pit_entry(name3) and self.fib.find_fib_entry(name3):
                    to_lower.put([faceid, Interest(name3)])
                if not self.pit.find_pit_entry(name4) and self.fib.find_fib_entry(name4):
                    to_lower.put([faceid, Interest(name4)])
                self._ca_table[packet.name] = ca_entry

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

            # Interest for available chunks
            if "CA" in string_components[-1]:
                self.pass_through = True  # This node doesn't handle CA content, only forwards to neighbours
                chunks_available = self.get_chunks_available(packet)
                if last == b"CA0" or isinstance(chunks_available, Content):  # If there are chunks available, return them
                    to_lower.put([faceid, chunks_available])
                else:  # Otherwise try to pass on interest to neighbour
                    to_lower.put([faceid, Interest(self.decrease_name(packet.name))])

            # General Interest passed on to chunklayer
            elif "CL" in string_components[-1]:
                matching_content = self.get_matching_content_from_packed_name(packet)
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
            ca_content = False
            cl_content = False

            # Metadata or string containing available chunks from neighbour
            if "CA" in string_components[-1]:
                self.cs.remove_content_object(packet.name)  # Remove from cs, so next interest comes through to chunklayer
                if string_components[-1] == f"CA{self.num_of_forwards}":  # This is the requesting node --> unpack
                    ca_content = True
                    ca_entry = self._ca_table.get(self.unpack(packet.name))
                    # In order to be able to request the available chunks from the sender of this packet,
                    # we need to safe the first component.
                    # This is then used in pack_ca() to send packet to the correct recipient.
                    ca_entry.recipient = Name(components[:1])
                    # Only replace existing list of available chunks if it contains more chunks
                    self.save_if_longest(packet, ca_entry)
                    if components[0] == b"nL":
                        ca_entry.answer_L = True
                    else:
                        ca_entry.answer_R = True
                    if ca_entry.answer_L and ca_entry.answer_R:  # We have a response from both neighbours and can proceed
                        packet = ca_entry.ca
                        self._request_table.append(RequestTableEntry(packet.name))
                    self._ca_table[self.unpack(packet.name)] = ca_entry
                else:  # This is not the requesting node --> pass on to neighbour
                    to_lower.put([faceid, Content(self.increase_name(packet.name), packet.content)])
                    return

            # Content from the chunklayer of a neighbouring node
            elif "CL" in string_components[-1]:
                if string_components[-1] == f"CL{self.num_of_forwards}":  # This is the requesting node --> unpack
                    cl_content = True
                    packet.name = self.unpack(packet.name)
                    # Save the sender of this packet as the recipient for further interests. Used in pack_cl()
                    self.recipient_cl[packet.name] = Name(components[:1])
                else:  # This is not the requesting node --> pass on to neighbour
                    to_lower.put([faceid, Content(self.increase_name(packet.name), packet.content)])
                    return

            request_entry = self.get_request_entry(packet.name)
            if request_entry is None:
                return
            self._request_table.remove(request_entry)
            if "CA" in components[-2].decode("utf-8"):
                if self.pass_through:
                    return
                ca_content = True
                request_entry.chunked = True
            self.handle_content(faceid, packet, request_entry, ca_content, cl_content, to_lower, to_higher)

        elif isinstance(packet, Nack):
            if self.prefix not in string_components[0]:
                request_entry = self.get_request_entry(packet.name)
                if request_entry:
                    self._request_table.remove(request_entry)
                if "CA" in string_components[-1]:
                    if string_components[-1] == f"CA{self.num_of_forwards}":  # This is the requesting node
                        unpacked = self.unpack(packet.name)
                        ca_entry = self._ca_table.get(unpacked)
                        if components[0] == b"nL":
                            ca_entry.answer_L = True
                        else:
                            ca_entry.answer_R = True
                        if ca_entry.answer_L and ca_entry.answer_R:  # We have an answer from both neighbour
                            if ca_entry.ca:  # We have chunks available from one of the neighbours
                                packet = ca_entry.ca
                                self._ca_table[unpacked] = ca_entry
                                self.handle_content(faceid, packet, RequestTableEntry(packet.name), True, False,
                                                    to_lower, to_higher)
                                return
                            else:
                                ca_entry.received_all = True
                                request_entry = self.get_request_entry(unpacked)
                                if request_entry and not request_entry.requested_md and not self.pass_through:
                                    self.creat_chunk_interests(faceid, request_entry, to_lower)

                        self._ca_table[unpacked] = ca_entry
                    else:  # This is not the requesting node --> pass on to neighbour
                        name = self.increase_name(packet.name)
                        nack = Nack(name, NackReason.NO_CONTENT, Interest(name))
                        to_lower.put([faceid, nack])
                elif "CL" in string_components[-1]:
                    if string_components[-1] != f"CL{self.num_of_forwards}":  # This is not the requesting node --> pass on to neighbour
                        name = self.increase_name(packet.name)
                        nack = Nack(name, NackReason.NO_CONTENT, Interest(name))
                        to_lower.put([faceid, nack])
                else:
                    to_higher.put([faceid, packet])
                self.pit.remove_pit_entry(packet.name)
            else:
                if "c" in string_components[-1]:
                    packet.name.components = components[:-1]
                    to_higher.put([faceid, Nack(packet.name, NackReason.NO_CONTENT, Interest(packet.name))])
                else: #FIXME What to do here?
                    # to_higher.put([faceid, packet])
                    pass

    def handle_content(self, faceid: int, packet: Content, request_entry: RequestTableEntry, ca_content: bool,
                       cl_content: bool, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """Handle incoming content"""
        if request_entry.chunked is False:  # Not chunked content
            if not packet.get_bytes().startswith(b'mdo:'):
                if ca_content:
                    self.handle_ca(faceid, packet, to_lower)
                else:
                    to_higher.put([faceid, packet])
                return
            else:  # Received metadata data --> chunked content
                request_entry.chunked = True
        if packet.get_bytes().startswith(b'mdo:'):  # Request all frames from meta data
            self.handle_received_meta_data(faceid, packet, request_entry, to_lower, ca_content, cl_content)
        else:
            self.handle_received_chunk_data(faceid, packet, request_entry, to_lower, to_higher, ca_content)

    def handle_received_meta_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                  to_lower: multiprocessing.Queue, ca_content: bool, cl_content: bool):
        """Handle meta data"""
        if packet.name in request_entry.requested_md:
            request_entry.requested_md.remove(packet.name)
        md, chunks, size = self.chunkifyer.parse_meta_data(packet.content)
        for chunk in chunks:  # Request all chunks from the meta data file if not already received or requested
            if chunk not in request_entry.requested_chunks and chunk not in [i.name for i in request_entry.chunks]:
                request_entry.requested_chunks.append(chunk)
        if md is not None:  # There is another md file
            if md not in request_entry.requested_md:
                request_entry.requested_md.append(md)
                if cl_content:
                    md = self.pack_cl(md)
                to_lower.put([faceid, Interest(md)])
        else:
            # Only create interests if it is the requesting node handling this metadata and
            # either the packet is CA content or there is no CA content available
            if not self.pass_through:
                if ca_content:
                    self.creat_chunk_interests(faceid, request_entry, to_lower)
                elif self._ca_table.get(request_entry.name).received_all:  # We have an answer from both neighbours
                    self.creat_chunk_interests(faceid, request_entry, to_lower)

                # if ca_content or self._ca_table.get(request_entry.name).received_all:
                #     self.creat_chunk_interests(faceid, request_entry, to_lower)

        self._chunk_table[packet.name] = (packet, time.time())
        self._request_table.append(request_entry)

    def handle_received_chunk_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, ca_content: bool):
        """Handle chunk data"""
        if packet.name in request_entry.requested_chunks:
            request_entry.requested_chunks.remove(packet.name)
            request_entry.chunks.append(packet)
        self._chunk_table[packet.name] = (packet, time.time())
        if not request_entry.requested_chunks:
            if (request_entry.name in self._ca_table.keys() and self._ca_table.get(request_entry.name).completely_available) \
                    or not request_entry.requested_md:  # All chunks are available
                data = request_entry.chunks
                data = sorted(data, key=lambda content: int(''.join(filter(str.isdigit, content.name.string_components[-1]))))
                cont = self.chunkifyer.reassamble_data(request_entry.name, data)
                if ca_content:
                    self.handle_ca(faceid, cont, to_lower)
                else:
                    del self._ca_table[request_entry.name]
                    to_higher.put([faceid, cont])
                return

        self._request_table.append(request_entry)

    def handle_ca(self, faceid: int, content: Content, to_lower: multiprocessing.Queue):
        """Unpack the received ca message and create interests for all available chunks."""
        content.name = self.unpack(content.name)
        ca_entry = self._ca_table.get(content.name)
        ca_entry.received_all = True

        chunks_str = content.content.split(";")
        chunks = [Name(chunk) for chunk in chunks_str]

        request_entry = self.get_request_entry(content.name)
        if request_entry and not self.pass_through:
            if chunks_str[0] == "complete":  # Neighbour has complete data
                chunks.pop(0)
                ca_entry.completely_available = True  # Ignore requested_md, because neighbour has all chunks
            self._ca_table[content.name] = ca_entry
            self._request_table.remove(request_entry)
            # Create interests for all chunks that are available from neighbour
            for chunk in chunks:
                print("TO NEIGHBOUR:", self.pack_ca(chunk, ca_entry))
                if chunk not in request_entry.requested_chunks and chunk not in [i.name for i in request_entry.chunks]:
                    request_entry.requested_chunks.append(chunk)
                to_lower.put([faceid, Interest(self.pack_ca(chunk, ca_entry))])
            self._request_table.append(request_entry)

            # If there is no name in requested_md try to request the remaining chunks.
            # This is only necessary to get a NACK, so the simulation continues.
            if not request_entry.requested_md:
                for chunk in request_entry.requested_chunks:
                    if chunk not in chunks:
                        print("TO ORIGINAL SOURCE:", chunk)
                        to_lower.put([faceid, Interest(chunk)])

    def get_request_entry(self, name: Name):
        """
        Check if a name is in the request table.
        Return entry or None.
        """
        for entry in self._request_table:
            if entry.name == name or name in entry.requested_chunks or name in entry.requested_md:
                return entry
        return None

    def get_chunks_available(self, packet: Packet):
        """
        Check if chunks are available for a given name.
        Return a content object containing the names of the available chunks, or NACK
        """
        chunks_available = []
        name = self.unpack(packet.name)
        request_entry = self.get_request_entry(name)
        cs_entry = self.cs.find_content_object(name)

        if request_entry is not None:
            chunks_available = [str(chunk.name) for chunk in request_entry.chunks]

        elif cs_entry:
            chunks_available.append("complete")
            meta_data = cs_entry.content
            _, _, content_size = self.chunkifyer.parse_meta_data(meta_data.content)
            number_of_chunks = math.ceil(int(content_size) / self.chunk_size)
            chunks_available += [f"{name}/c{i}" for i in range(number_of_chunks)]

        if chunks_available:
            chunks_available = Content(packet.name, ";".join(chunks_available))
            if len(chunks_available.content) > self.chunk_size:
                meta_data, chunks = self.chunkifyer.chunk_data(chunks_available)
                meta_data.extend(chunks)
                for data in meta_data:
                    self.cs.remove_content_object(data.name)
                    self.cs.add_content_object(data)
                return meta_data[0]
            else:
                return chunks_available

        return Nack(packet.name, NackReason.NO_CONTENT, packet)

    def get_matching_content_from_packed_name(self, packet: Packet):
        """Return either the content matching the unpacked name or NACK"""
        name_in = self.unpack(packet.name)
        if name_in in self._chunk_table:
            matching_content = self._chunk_table.get(name_in)[0]
            matching_content.name = packet.name
            return matching_content
        else:
            return Nack(packet.name, NackReason.NO_CONTENT, packet)

    def creat_chunk_interests(self, faceid: int, request_entry: RequestTableEntry, to_lower: multiprocessing.Queue):
        """Create interests for all the chunks in requested_md of the specified request table entry."""
        for chunk in request_entry.requested_chunks:
            print("TO ORIGINAL SOURCE:", chunk)
            to_lower.put([faceid, Interest(chunk)])

    def save_if_longest(self, packet: Content, ca_entry: CaEntry):
        """
        Check if the received ca content is longer than the existing one and if so, replace it.
        In the case where both neighbours have chunks available, we want to send the interests only to the one
        which has more.
        """
        if packet.get_bytes().startswith(b'mdo:'):  # Content is metadata, read size from metadata
            _, _, content_size = self.chunkifyer.parse_meta_data(packet.content)
        else:  # Content is string, size equals length of the string
            content_size = (len(packet.content))
        content_size = int(content_size)
        if content_size > ca_entry.size:
            ca_entry.ca = packet

    def pack_ca(self, name: Name, ca_entry: CaEntry) -> Name:
        """Prepend the recipient, append "CL" and the number of forwards."""
        return ca_entry.recipient + name + f"CL{self.num_of_forwards}"

    def pack_cl(self, name: Name) -> Name:
        """Prepend the recipient, append "CA" and the number of forwards."""
        lookup_name = Name(name.components[:-1])
        return self.recipient_cl.get(lookup_name) + name + f"CL{self.num_of_forwards}"

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
        if "CA" in last:
            return Name(components[:-1]) + f"CA{i+1}"
        elif "CL" in last:
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
        if "CA" in last:
            return Name(components[:-1]) + f"CA{i-1}"
        elif "CL" in last:
            return Name(components[:-1]) + f"CL{i-1}"
        return name
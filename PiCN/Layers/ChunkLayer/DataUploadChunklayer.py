""""Basic Chunking Layer for PICN"""

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
    """Request table for Pending chunks"""

    def __init__(self, name: Name):
        self.name: Name = name
        self.requested_chunks = []
        self.chunks =[]
        self.requested_md = []
        self.chunked = False
        self.last_chunk: Name

    def __eq__(self, other):
        return self.name == other.name


class DataTest3(LayerProcess):
    """"Basic Chunking Layer for PICN"""

    def __init__(self, cs: BaseContentStore, pit: BasePendingInterestTable, fib: BaseForwardingInformationBase,
                 chunk_size: int=4, num_of_forwards: int=1, log_level: int=255):
        super().__init__("ChunkLayer", log_level=log_level)
        self.cs = cs
        self.pit = pit
        self.fib = fib
        self.chunk_size = chunk_size
        self.chunkifyer = SimpleContentChunkifyer(chunk_size)
        self.num_of_forwards = num_of_forwards

        manager = multiprocessing.Manager()
        self._chunk_table: Dict[Name, (Content, float)] = manager.dict()
        self._request_table: List[RequestTableEntry] = manager.list()
        self.ca_nack_L = True
        self.ca_nack_R = True
        self.ca_cont_L = True
        self.ca_cont_R = True
        self.ca_done = False
        self.pass_through = True
        self.recipient_ca = []
        self.recipient_cl = []
        self.ca: Dict[int, Content] = {}
        self.chunks_available_from_neighbour: Dict[Name, List[Name]] = {}

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Got Data from higher")
        faceid = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest " + str(packet.name))
            request_entry = self.get_request_entry(packet.name)
            if request_entry is None:
                self._request_table.append(RequestTableEntry(packet.name))

            # If the interest starts with /car and not ends with NFN, request metadata and available chunks from neighbours
            components = packet.name.components
            if components[0] == b"car" and components[-1] != b"NFN" and not request_entry:
                self.pass_through = False
                name1 = Name("/nL") + packet.name + f"CA{self.num_of_forwards}"
                name2 = Name("/nR") + packet.name + f"CA{self.num_of_forwards}"
                name3 = Name("/nL") + packet.name + f"CL{self.num_of_forwards}"
                name4 = Name("/nR") + packet.name + f"CL{self.num_of_forwards}"
                if not self.pit.find_pit_entry(name1) and self.fib.find_fib_entry(name1):
                    self.ca_nack_L = False
                    self.ca_cont_L = False
                    self.ca_done = False
                    to_lower.put([faceid, Interest(name1)])
                if not self.pit.find_pit_entry(name2) and self.fib.find_fib_entry(name2):
                    self.ca_nack_R = False
                    self.ca_cont_R = False
                    self.ca_done = False
                    to_lower.put([faceid, Interest(name2)])
                if not self.pit.find_pit_entry(name3) and self.fib.find_fib_entry(name3):
                    to_lower.put([faceid, Interest(name3)])
                if not self.pit.find_pit_entry(name4) and self.fib.find_fib_entry(name4):
                    to_lower.put([faceid, Interest(name4)])
            to_lower.put(data)
            return

        elif isinstance(packet, Content):
            self.logger.info("Packet is Content (name=%s, %d bytes)" %(str(packet.name), len(packet.content)))
            if len(packet.content) < self.chunk_size:
                to_lower.put(data)
            else:
                self.logger.info("Chunking Packet")
                metadata, chunks = self.chunkifyer.chunk_data(packet)  # create metadata and chunks
                self.logger.info("Metadata: " + metadata[0].content)
                to_lower.put([faceid, metadata[0]])  # return name of first metadata object
                for md in metadata:  # add metadata to chunktable
                    if md.name not in self._chunk_table:
                        self._chunk_table[md.name] = (md, time.time())
                for c in chunks:  # add chunks to chunktable
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
        last = components[-1]
        last_string = last.decode("utf-8")

        if isinstance(packet, Interest):
            self.logger.info("Packet is Interest")

            # Interest for available chunks
            if "CA" in last_string:
                self.pass_through = True  # This node doesn't handle CA content, only forwards to neighbours
                chunks_available = self.get_chunks_available(packet)
                if last == b"CA0" or isinstance(chunks_available, Content):  # If there are chunks available, return them
                    to_lower.put([faceid, chunks_available])
                else:  # Otherwise try to pass on interest to neighbour
                    to_lower.put([faceid, Interest(self.decrease_name(packet.name))])

            # General Interest passed on to chunklayer
            elif "CL" in last_string:
                matching_content = self.get_matching_content(self.unpack(packet.name), packet.name)
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
            if "CA" in last_string:
                self.cs.remove_content_object(packet.name)  # Remove from cs, so next interest comes through to chunklayer
                if last_string == f"CA{self.num_of_forwards}":  # This is the requesting node -> unpack
                    ca_content = True
                    self.recipient_ca = components[:1]  # Save sender as recipient for CA interests
                    self.save_content_by_length(packet)
                    if components[0] == b"nL":
                        self.ca_cont_L = True
                    else:
                        self.ca_cont_R = True
                    if self.ca_complete():
                        packet = self.ca[max(self.ca)]  # Pick the longest entry
                        self._request_table.append(RequestTableEntry(packet.name))
                else:  # This is not the requesting node -> pass on to neighbour
                    to_lower.put([faceid, Content(self.increase_name(packet.name), packet.content)])
                    return

            # Content from the chunklayer of a neighbouring node
            elif "CL" in last_string:
                if last_string == f"CL{self.num_of_forwards}":  # This is the requesting node -> unpack
                    cl_content = True
                    self.recipient_cl = components[:1]  # Save sender as recipient for CL interests
                    packet.name = self.unpack(packet.name)
                else:  # This is not the requesting node -> pass on to neighbour
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
            if components[0] != b"car":
                request_entry = self.get_request_entry(packet.name)
                if request_entry:
                    self._request_table.remove(request_entry)
                if "CA" in last_string:
                    if last_string == f"CA{self.num_of_forwards}":  # This is the requesting node
                        if components[0] == b"nL":
                            self.ca_nack_L = True
                        else:
                            self.ca_nack_R = True
                        if self.ca_nack_L and self.ca_nack_R:  # No chunks available from either neighbour
                            self.ca_done = True
                            packet.name = self.unpack(packet.name)
                            request_entry = self.get_request_entry(packet.name)
                            if request_entry and not request_entry.requested_md and not self.pass_through:
                                self.creat_chunk_interests(faceid, request_entry, to_lower)
                        elif self.ca_complete():  #
                            packet = self.ca[max(self.ca)]  # Pick the longest entry
                            self.handle_content(faceid, packet, RequestTableEntry(packet.name), True, False, to_lower, to_higher)
                    else:  # This is not the requesting node -> pass on to neighbour
                        name = self.increase_name(packet.name)
                        nack = Nack(name, NackReason.NO_CONTENT, Interest(name))
                        to_lower.put([faceid, nack])
                elif "CL" in last_string:
                    if last_string != f"CL{self.num_of_forwards}":  # This is not the requesting node -> pass on to neighbour
                        name = self.increase_name(packet.name)
                        nack = Nack(name, NackReason.NO_CONTENT, Interest(name))
                        to_lower.put([faceid, nack])
                self.pit.remove_pit_entry(packet.name)
            else:
                if "c" in last_string:
                    packet.name.components = components[:-1]
                    to_higher.put([faceid, Nack(packet.name, NackReason.NO_CONTENT, Interest(packet.name))])
                else: #FIXME What to do here?
                    pass
                    # to_higher.put([faceid, packet])

    def handle_received_meta_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                  to_lower: multiprocessing.Queue, ca_content: bool, cl_content: bool):
        """Handle the case, where metadata are received from the network"""
        if packet.name in request_entry.requested_md:
            request_entry.requested_md.remove(packet.name)
        md, chunks, size = self.chunkifyer.parse_meta_data(packet.content)
        for chunk in chunks:  # request all chunks from the metadata file if not already received or requested
            if chunk not in request_entry.requested_chunks and chunk not in [i.name for i in request_entry.chunks]:
                request_entry.requested_chunks.append(chunk)
        if md is not None:  # there is another md file
            if md not in request_entry.requested_md:
                request_entry.requested_md.append(md)
                if cl_content:
                    md = self.pack_cl(md)
                to_lower.put([faceid, Interest(md)])
        else:
            request_entry.last_chunk = chunks[-1]
            # Only create interests if it is the requesting node handling this metadata and
            # either the packet is CA content or there is no CA content available
            if (ca_content or self.ca_done) and not self.pass_through:
                self.creat_chunk_interests(faceid, request_entry, to_lower)
        self._chunk_table[packet.name] = (packet, time.time())
        self._request_table.append(request_entry)

    def handle_received_chunk_data(self, faceid: int, packet: Content, request_entry: RequestTableEntry,
                                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, ca_content: bool):
        """Handle the case where chunk data are received from the network"""
        if packet.name in request_entry.requested_chunks:
            request_entry.requested_chunks.remove(packet.name)
            request_entry.chunks.append(packet)
        self._chunk_table[packet.name] = (packet, time.time())
        if not request_entry.requested_chunks and not request_entry.requested_md:  # all chunks are available
            data = request_entry.chunks
            data = sorted(data, key=lambda content: int(''.join(filter(str.isdigit, content.name.string_components[-1]))))
            cont = self.chunkifyer.reassamble_data(request_entry.name, data)
            if ca_content:
                self.handle_ca(faceid, cont, to_lower)
            else:
                to_higher.put([faceid, cont])
        else:
            self._request_table.append(request_entry)

    def get_request_entry(self, name: Name):
        """check if a name is in the request table"""
        for entry in self._request_table:
            if entry.name == name or name in entry.requested_chunks or name in entry.requested_md:
                return entry
        return None

    def get_chunks_available(self,  packet: Packet):
        """
        Check if chunks are available for a given name.
        Return a content object containing the names of the available chunks, or NACK
        """
        request_entry = self.get_request_entry(self.unpack(packet.name))
        if request_entry is not None:
            chunks_available = [chunk.name.to_string() for chunk in request_entry.chunks]
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

    def get_matching_content(self, name_in: Name, name_out: Name):
        """returns either the content matching the name_in or Nack"""
        if name_in in self._chunk_table:
            matching_content = self._chunk_table.get(name_in)[0]
            matching_content.name = name_out
            return matching_content
        else:
            return Nack(name_out, NackReason.NO_CONTENT, Interest(name_out))

    def handle_ca(self, faceid: int, content: Content, to_lower: multiprocessing.Queue):
        """
        Unpacks the received ca message, and stores the available chunks in a list.
        Invokes the creation of the interests for the chunks, if the corresponding metadata has been received completely.
        """
        self.ca_done = True
        content.name = self.unpack(content.name)
        chunks = []
        for chunk in content.content.split(";"):
            chunks.append(Name(chunk))
        self.chunks_available_from_neighbour[content.name] = chunks
        request_entry = self.get_request_entry(content.name)
        if request_entry and not request_entry.requested_md and not self.pass_through:
            self.creat_chunk_interests(faceid, request_entry, to_lower)

    def handle_content(self, faceid: int, packet: Content, request_entry: RequestTableEntry, ca_content: bool,
                       cl_content: bool, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """Handles incoming content"""
        if request_entry.chunked is False:  # not chunked content
            if not packet.get_bytes().startswith(b'mdo:'):
                if ca_content:
                    self.handle_ca(faceid, packet, to_lower)
                else:
                    to_higher.put([faceid, packet])
                return
            else:  # Received metadata data --> chunked content
                request_entry.chunked = True
        if packet.get_bytes().startswith(b'mdo:'):  # request all frames from metadata
            self.handle_received_meta_data(faceid, packet, request_entry, to_lower, ca_content, cl_content)
        else:
            self.handle_received_chunk_data(faceid, packet, request_entry, to_lower, to_higher, ca_content)

    def creat_chunk_interests(self, faceid: int, request_entry: RequestTableEntry, to_lower: multiprocessing.Queue):
        """
        Creates interests for all the chunks in requested_md of the specified request table entry.
        All interests for chunks that are available from a neighbour get sent to neighbour.
        """
        if request_entry.name in self.chunks_available_from_neighbour.keys():
            from_neighbour = self.chunks_available_from_neighbour.get(request_entry.name)
            for chunk in from_neighbour:
                print("TO NEIGHBOUR:", self.pack_ca(chunk))
                to_lower.put([faceid, Interest(self.pack_ca(chunk))])
            to_original_source = [x for x in request_entry.requested_chunks if x not in from_neighbour]
        else:
            to_original_source = request_entry.requested_chunks
        for chunk in to_original_source:
            print("TO ORIGINAL SOURCE:", chunk)
            to_lower.put([faceid, Interest(chunk)])

    def save_content_by_length(self, packet: Content):
        """
        Save the available chunks along with the length of the string (-> the number of available chunks).
        If two neighbours have chunks available, we can pick the one who offers more.
        """
        if packet.get_bytes().startswith(b'mdo:'):  # Content is metadata, read size from metadata
            self.ca[int(packet.content.split(":")[1])] = packet
        else:  # Content is string, size equals length of the string
            self.ca[int(len(packet.content))] = packet

    def pack_ca(self, name: Name) -> Name:
        return Name(self.recipient_ca) + name + f"CL{self.num_of_forwards}"

    def pack_cl(self, name: Name) -> Name:
        return Name(self.recipient_cl) + name + f"CL{self.num_of_forwards}"

    def unpack(self, name: Name) -> Name:
        return Name(name.components[1:-1])

    def increase_name(self, name: Name) -> Name:
        components = name.components
        last = components[-1].decode("utf-8")
        i = int(''.join(filter(str.isdigit, last)))
        if "CA" in last:
            return Name(components[:-1]) + f"CA{i+1}"
        elif "CL" in last:
            return Name(components[:-1]) + f"CL{i+1}"
        return name

    def decrease_name(self, name: Name) -> Name:
        components = name.components
        last = components[-1].decode("utf-8")
        i = int(''.join(filter(str.isdigit, last)))
        if "CA" in last:
            return Name(components[:-1]) + f"CA{i-1}"
        elif "CL" in last:
            return Name(components[:-1]) + f"CL{i-1}"
        return name

    def ca_complete(self) -> bool:
        """
        Check if CA content or NACKs have been received.
        The only case not checked here is the one where both neighbours return NACK.
        """
        return (self.ca_nack_L and self.ca_cont_R) or (self.ca_cont_L and self.ca_nack_R) or \
               (self.ca_cont_L and self.ca_cont_R)

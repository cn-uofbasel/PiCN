"""Repository Layer"""

import multiprocessing
import mmap
import math
import hashlib

from PiCN.Layers.ICNLayer.ContentStore.ContentStoreMemoryExact import ContentStoreMemoryExact
from PiCN.Packets import Content, Interest, Packet, Nack, NackReason, Name
from PiCN.Processes import LayerProcess
from PiCN.Playground.AssistedSharing.SampleData import alice_index_schema


class RepoLayer(LayerProcess):

    def __init__(self, log_level=255, manager: multiprocessing.Manager=None):
        super().__init__(logger_name="ICNLayer", log_level=log_level)
        if manager is None:
            manager = multiprocessing.Manager()
        self._data_structs = manager.dict()
        cs = ContentStoreMemoryExact()
        cs.add_content_object(Content("/alice/schema.index", alice_index_schema))
        self._data_structs['cs'] = cs
        self._files = {"/alice/movies/cats-and-dogs.mp4" : "/tmp/cats-and-dogs.mp4",
                       "/alice/img/basel.jpg" : "/tmp/basel.jpg"}


    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass


    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if len(data) != 2:
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if type(data[0]) != int:
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return
        if not isinstance(data[1], Packet):
            self.logger.info("ICN Layer expects to receive [face id, packet] from lower layer")
            return

        face_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.handle_interest(face_id, packet, to_lower, to_higher, False)
        elif isinstance(packet, Content):
            self.logger.info("Received Data Packet, do nothing")
            return
        elif isinstance(packet, Nack):
            self.logger.info("Received NACK, do nothing")
            return
        else:
            self.logger.info("Received Unknown Packet, do nothing")
            return


    def handle_interest(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, from_local: bool = False):

         cs_entry = self.cs.find_content_object(interest.name)
         if cs_entry is not None:
             self.logger.info("Found in cache")
             to_lower.put([face_id, cs_entry.content])
             return
         else:
             self.logger.info("Not found in cache, try to generate")
             self.generate_data(interest.name)
             cs_entry = self.cs.find_content_object(interest.name)
             if cs_entry is not None:
                 manifest = self.cs.find_content_object(interest.name).content
                 to_lower.put([face_id, manifest])
                 return
             else:
                  nack = Nack(interest.name, NackReason.NO_CONTENT, interest=interest)
                  to_lower.put([face_id, nack])


    def generate_data(self, network_name: Name):
        fs_name = self._files[network_name.to_string()]
        with open(fs_name, "r+") as f:
            # open file and determine number of chunks
            file = mmap.mmap(f.fileno(), 0)
            file_length = len(file)
            num_chunks = math.ceil(file_length / 4096) # chunk size: 4096 bytes
            # generate data packets (manifest and chunk)
            chunk_names = list()
            for n in range(0, num_chunks-1):
                # extract chunk and compute digest
                chunk = file[4096 * n : min(4096*(n+1), file_length)]
                m = hashlib.sha256()
                m.update(chunk)
                digest = m.hexdigest()
                chunk_network_name = Name(network_name.to_string() + '/chunk/' + digest)
                # add to cs and chunk list
                chunk_names.append(chunk_network_name.to_string())
                self.add_to_cs(Content(chunk_network_name, chunk))
            # generate manifest
            manifest_data = "\n".join(chunk_names)
            manifest = Content(network_name, manifest_data)
            self.add_to_cs(manifest)

    @property
    def cs(self):
        """The Content Store"""
        return self._data_structs.get('cs')

    @cs.setter
    def cs(self, cs):
        self._data_structs['cs'] = cs

    def add_to_cs(self, content: Content):
        #cs = self._data_structs.get('cs')
        cs = self.cs
        cs.add_content_object(content)
        # self._data_structs['cs'] = cs
        self.cs = cs

    def ageing(self):
            pass

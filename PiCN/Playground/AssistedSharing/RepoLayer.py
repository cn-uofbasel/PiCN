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
        cache = ContentStoreMemoryExact()
        cache.add_content_object(Content("/alice/schema.index", alice_index_schema))
        self._data_structs['cache'] = cache
        self._files_in_repo = {"/alice/movies/cats-and-dogs.mp4" : "/tmp/cats-and-dogs.mp4",
                       "/alice/public/img/basel.jpg" : "/tmp/basel.jpg"}


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
            self.handle_interest(face_id, packet, to_lower)
        elif isinstance(packet, Content):
            self.logger.info("Received Data Packet, do nothing")
            return
        elif isinstance(packet, Nack):
            self.logger.info("Received NACK, do nothing")
            return
        else:
            self.logger.info("Received Unknown Packet, do nothing")
            return

    def handle_interest(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue):
        """
        Handle incoming interest
        :param face_id: ID of incoming face
        :param interest: Interest
        :param to_lower: Queue to lower layer
        :return: None
        """
        cache_entry = self.cache.find_content_object(interest.name)
        if cache_entry is not None:
            self.logger.info("Found in cache")
            to_lower.put([face_id, cache_entry.content])
            return
        else:
            if self.generate_data(interest.name) is False:
                nack = Nack(interest.name, NackReason.NO_CONTENT, interest=interest)
                to_lower.put([face_id, nack])
                self.logger.info("Object not in repo")
                return
            else:
                self.logger.info("Not found in cache, successfully generated")
                manifest = self.cache.find_content_object(interest.name).content
                to_lower.put([face_id, manifest])
                return

    def generate_data(self, network_name: Name, chunk_size: int = 4096):
        """
        Generates manifest and chunks for a file in the repo
        :param network_name: Network name of high-level object
        :param chunk_size: chunk size
        :return: True if successful, False otherwise
        """
        try:
            fs_name = self._files_in_repo[network_name.to_string()]
        except:
            return False
        with open(fs_name, "r+") as f:
            # open file and determine number of chunks
            file = mmap.mmap(f.fileno(), 0)
            file_length = len(file)
            num_chunks = math.ceil(file_length / chunk_size)
            # generate data packets (manifest and chunk)
            chunk_names = list()
            for n in range(0, num_chunks+1):
                # extract chunk and compute digest
                chunk = file[chunk_size * n : min(chunk_size*(n+1), file_length)]
                m = hashlib.sha256()
                m.update(chunk)
                digest = m.hexdigest()
                chunk_network_name = Name(network_name.to_string() + '/chunk/' + digest)
                # add to cache and chunk list
                chunk_names.append(chunk_network_name.to_string())
                self.add_to_cache(Content(chunk_network_name, chunk))
            # generate manifest
            manifest_data = "\n".join(chunk_names)
            manifest = Content(network_name, manifest_data)
            self.add_to_cache(manifest)
            return True

    @property
    def cache(self):
        """
        Get Cache
        :return: Cache
        """
        return self._data_structs.get('cache')

    @cache.setter
    def cache(self, cache):
        """
        Set cache
        :param cache: Cache to store
        :return: None
        """
        self._data_structs['cache'] = cache

    def add_to_cache(self, content: Content):
        """
        Add a content object to the repositories cache
        :param content: Content object to add
        :return: None
        """
        cache = self.cache
        cache.add_content_object(content)
        self.cache = cache

    def ageing(self):
            pass # data should not be deleted from cache

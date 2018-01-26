"""A ICN Repository using PiCN"""

import multiprocessing

from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.RepositoryLayer.Repository import SimpleFileSystemRepository
from PiCN.Layers.RepositoryLayer.Repository import FlicFileSystemRepository
from PiCN.Logger import Logger
from PiCN.Packets import Name
from PiCN.Mgmt import Mgmt

# ----------------------------------------------------------------------

class ICNDataRepository(object):
    """A ICN Forwarder using PiCN"""

    def __init__(self, repotype: str, foldername: str,
                       prefix: Name, port=9000, debug_level=255):

        logger = Logger("ICNRepo", debug_level)
        logger.info("Start PiCN FLIC Repository on port %d, prefix %s" % \
                    (port, str(prefix)))

        #packet encoder
        if prefix.suite == 'ndn2013':
            self.encoder = NdnTlvEncoder()
        else:
            self.encoder = SimpleStringEncoder()

        #chunkifyer
        self.chunkifyer = SimpleContentChunkifyer()

        #repo
        if repotype == 'simple':
            self.repo = SimpleFileSystemRepository(foldername, prefix, logger)
        elif repotype == 'flic':
            self.repo = FlicFileSystemRepository(foldername, prefix, logger)
        else:
            print("ERROR: unknown repo type %s" % repotype)
            return

        #initialize layers
        self.linklayer = UDP4LinkLayer(port, debug_level=debug_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, debug_level=debug_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, debug_level=debug_level)
        self.repolayer = BasicRepositoryLayer(self.repo, debug_level=debug_level)

        #setup communication queues
        self.q_link_packet_up = multiprocessing.Queue()
        self.q_packet_link_down = multiprocessing.Queue()

        self.q_packet_chunk_up = multiprocessing.Queue()
        self.q_chunk_packet_down = multiprocessing.Queue()

        self.q_chunk_to_repo_up = multiprocessing.Queue()
        self.q_repo_to_chunk_down = multiprocessing.Queue()

        #set link layer queues
        self.linklayer.queue_to_higher = self.q_link_packet_up
        self.linklayer.queue_from_higher = self.q_packet_link_down

        #set packet encoding layer queues
        self.packetencodinglayer.queue_to_lower = self.q_packet_link_down
        self.packetencodinglayer.queue_from_lower = self.q_link_packet_up
        self.packetencodinglayer.queue_to_higher = self.q_packet_chunk_up
        self.packetencodinglayer.queue_from_higher = self.q_chunk_packet_down

        #set chunk layer queues
        self.chunklayer.queue_to_lower = self.q_chunk_packet_down
        self.chunklayer.queue_from_lower = self.q_packet_chunk_up
        self.chunklayer.queue_to_higher = self.q_chunk_to_repo_up
        self.chunklayer.queue_from_higher = self.q_repo_to_chunk_down

        #set repo layer queues
        self.repolayer.queue_from_lower = self.q_chunk_to_repo_up
        self.repolayer.queue_to_lower = self.q_repo_to_chunk_down

        # mgmt
        self.mgmt = Mgmt(None, None, None, self.linklayer, port,
                         self.start_repo, repo_path=foldername,
                         repo_prfx=prefix, debug_level=debug_level)

    def start_repo(self):
        # start processes
        self.linklayer.start_process()
        self.packetencodinglayer.start_process()
        self.chunklayer.start_process()
        self.repolayer.start_process()
        self.mgmt.start_process()

    def stop_repo(self):
        #Stop processes
        self.linklayer.stop_process()
        self.packetencodinglayer.stop_process()
        self.chunklayer.stop_process()
        self.repolayer.stop_process()
        self.mgmt.stop_process()

# eof

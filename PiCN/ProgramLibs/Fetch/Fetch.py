"""Fetch Tool for PiCN"""

import multiprocessing
from random import randint

from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack


class Fetch(object):
    """Fetch Tool for PiCN"""

    def __init__(self, ip: str, port: int, log_level = 255, encoder: BasicEncoder=None):

        #create encoder and chunkifyer
        if encoder == None:
            self.encoder = SimpleStringEncoder(log_level = log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()

        #create layers
        self.linklayer = UDP4LinkLayer(0, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, log_level=log_level)

        # setup communication queues
        self.q_link_packet_up = multiprocessing.Queue()
        self.q_packet_link_down = multiprocessing.Queue()
        self.q_packet_chunking_up = multiprocessing.Queue()
        self.q_chunking_packet_down = multiprocessing.Queue()
        self.q_chunking_up = multiprocessing.Queue()
        self.q_chunking_down = multiprocessing.Queue()

        # set link layer queues
        self.linklayer.queue_to_higher = self.q_link_packet_up
        self.linklayer.queue_from_higher = self.q_packet_link_down

        # set packet encoding layer queues
        self.packetencodinglayer.queue_to_lower = self.q_packet_link_down
        self.packetencodinglayer.queue_from_lower = self.q_link_packet_up
        self.packetencodinglayer.queue_to_higher = self.q_packet_chunking_up
        self.packetencodinglayer.queue_from_higher = self.q_chunking_packet_down

        self.chunklayer.queue_to_lower = self.q_chunking_packet_down
        self.chunklayer.queue_from_lower = self.q_packet_chunking_up
        self.chunklayer.queue_to_higher = self.q_chunking_up
        self.chunklayer.queue_from_higher = self.q_chunking_down

        # setup communication
        self.fid = self.linklayer.create_new_fid((ip, port), True)

        # send packet
        self.linklayer.start_process()
        self.packetencodinglayer.start_process()
        self.chunklayer.start_process()


    def fetch_data(self, name: Name) -> str:
        """Fetch data from the server"""
        # create interest
        interest: Interest = Interest(name)
        self.chunklayer.queue_from_higher.put([self.fid, interest])
        packet = self.chunklayer.queue_to_higher.get()[1]
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    def stop_fetch(self):
        """Close everything"""
        self.linklayer.stop_process()
        self.packetencodinglayer.stop_process()
        self.chunklayer.stop_process()
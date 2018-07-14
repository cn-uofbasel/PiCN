"""Fetch Tool for PiCN"""

from PiCN.LayerStack import LayerStack
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Name, Interest, Nack
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory


class Fetch(object):
    """Fetch Tool for PiCN"""

    def __init__(self, ip: str, port: int, log_level=255, encoder: BasicEncoder = None, interfaces=None):

        # create encoder and chunkifyer
        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()

        # initialize layers
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        if interfaces is None:
            interfaces = [UDP4Interface(0)]
        else:
            interfaces = interfaces

        # create layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.chunklayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        # setup communication
        if port is None:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo(ip, 0))
        else:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo((ip, port), 0))

        # send packet
        self.lstack.start_all()

    def fetch_data(self, name: Name, timeout=4.0) -> str:
        """Fetch data from the server
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        # create interest
        interest: Interest = Interest(name)
        self.lstack.queue_from_higher.put([self.fid, interest])
        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    def stop_fetch(self):
        """Close everything"""
        self.lstack.stop_all()
        self.lstack.close_all()

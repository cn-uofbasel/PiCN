"""Fetch Tool for PiCN"""

from PiCN.LayerStack import LayerStack
from PiCN.Layers.AutoconfigLayer import AutoconfigClientLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Processes.PiCNSyncDataStructFactory import PiCNSyncDataStructFactory
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack
from PiCN.Layers.TimeoutPreventionLayer import BasicTimeoutPreventionLayer, TimeoutPreventionMessageDict

class Fetch(object):
    """Fetch Tool for PiCN"""

    def __init__(self, ip: str, port: int, log_level=255, encoder: BasicEncoder=None, autoconfig: bool = False,
                 interfaces=None):

        # create encoder and chunkifyer
        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level = log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()

        # initialize layers
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.register("timeoutprevention_dict", TimeoutPreventionMessageDict)
        synced_data_struct_factory.create_manager()
        faceidtable = synced_data_struct_factory.manager.faceidtable()
        timeoutprevention_dict = synced_data_struct_factory.manager.timeoutprevention_dict()

        if interfaces is None:
            interfaces = [UDP4Interface(0)]
        else:
            interfaces = interfaces

        # create layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, log_level=log_level)
        self.timeoutpreventionlayer = BasicTimeoutPreventionLayer(timeoutprevention_dict, None, log_level=log_level)
        self.lstack: LayerStack = LayerStack([
            self.timeoutpreventionlayer,
            self.chunklayer,
            self.packetencodinglayer,
            self.linklayer
        ])
        self.timeoutpreventionlayer.ageing()
        self.autoconfig = autoconfig
        if autoconfig:
            self.autoconfiglayer: AutoconfigClientLayer = AutoconfigClientLayer(self.linklayer)
            self.lstack.insert(self.autoconfiglayer, on_top_of=self.packetencodinglayer)

        # setup communication
        if port is None:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo(ip, 0))
        else:
            self.fid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo((ip, port), 0))

        # send packet
        self.lstack.start_all()

    def fetch_data(self, name: Name, timeout=10.0) -> str:
        """Fetch data from the server
        :param name Name to be fetched
        :param timeout Timeout to wait for a response. Use 0 for infinity
        """
        # create interest
        interest: Interest = Interest(name)
        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])

        if timeout == 0:
            packet = self.lstack.queue_to_higher.get()[1]
        else:
            try:
                packet = self.lstack.queue_to_higher.get(timeout=timeout)[1]
            except:
                return "Timeout when handling the request"
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    def stop_fetch(self):
        """Close everything"""
        self.lstack.stop_all()
        self.lstack.close_all()

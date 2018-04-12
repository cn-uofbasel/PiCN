"""Fetch Tool for PiCN"""

from PiCN.LayerStack import LayerStack
from PiCN.Layers.AutoconfigLayer import AutoconfigClientLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Content, Name, Interest, Nack


class Fetch(object):
    """Fetch Tool for PiCN"""

    def __init__(self, ip: str, port: int, log_level = 255, encoder: BasicEncoder=None, autoconfig: bool = False):

        # create encoder and chunkifyer
        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level = log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder
        self.chunkifyer = SimpleContentChunkifyer()

        # create layers
        self.linklayer = UDP4LinkLayer(0, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.chunklayer = BasicChunkLayer(self.chunkifyer, log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.chunklayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        self.autoconfig = autoconfig
        if autoconfig:
            self.autoconfiglayer: AutoconfigClientLayer = AutoconfigClientLayer(self.linklayer,
                                                                                bcaddr='127.255.255.255', bcport=6363)
            self.lstack.insert(self.autoconfiglayer, on_top_of=self.packetencodinglayer)

        # setup communication
        self.fid = self.linklayer.create_new_fid((ip, port), True)

        # send packet
        self.lstack.start_all()

    def fetch_data(self, name: Name) -> str:
        """Fetch data from the server"""
        # create interest
        interest: Interest = Interest(name)
        if self.autoconfig:
            self.lstack.queue_from_higher.put([None, interest])
        else:
            self.lstack.queue_from_higher.put([self.fid, interest])
        packet = self.lstack.queue_to_higher.get()[1]
        if isinstance(packet, Content):
            return packet.content
        if isinstance(packet, Nack):
            return "Received Nack: " + str(packet.reason.value)
        return None

    def stop_fetch(self):
        """Close everything"""
        self.lstack.stop_all()
        self.lstack.close_all()

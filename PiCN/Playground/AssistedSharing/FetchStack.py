"""Fetch Stack"""

from PiCN.LayerStack import LayerStack
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import NdnTlvEncoder
from PiCN.Packets.Name import Name
from PiCN.Playground.AssistedSharing.FetchLayer import FetchLayer
from PiCN.Processes import PiCNSyncDataStructFactory


class FetchStack(object):
    """Fetch Stack"""

    def __init__(self, ip: str, port: int, high_level_name: Name, log_level=255):
        """

        :param ip:
        :param port:
        :param high_level_name:
        :param log_level:
        """
        """
        Create stack of layers for fetch tool (UDP only)
        :param ip: IP address of entry node to network
        :param port: Port address of entry node to network
        :param high_level_name: Name of high-level object to fetch 
        :param log_level: Log level
        """
        # create encoder
        self.encoder = NdnTlvEncoder()

        # create datastruct
        synced_data_struct_factory1 = PiCNSyncDataStructFactory()
        synced_data_struct_factory1.register("faceidtable", FaceIDDict)
        synced_data_struct_factory1.create_manager()
        faceidtable = synced_data_struct_factory1.manager.faceidtable()

        # create layers

        self.link_layer = BasicLinkLayer([UDP4Interface(0)], faceidtable, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.fetch_layer = FetchLayer(log_level)

        self.layer_stack: LayerStack = LayerStack([
            self.fetch_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        # setup face
        self.face_id = self.link_layer.faceidtable.get_or_create_faceid(AddressInfo((ip, port), 0))

        # start all layers in the stack
        self.layer_stack.start_all()

        # trigger fetch
        self.fetch_layer.trigger_fetching(high_level_name, self.face_id)

    def stop_fetch(self):
        """
        Stop all layers
        :return: None
        """
        self.layer_stack.stop_all()
        self.layer_stack.close_all()

"""Repository Stack"""

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.ICNLayer.ContentStore import ContentStorePersistentExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, NdnTlvEncoder
from PiCN.Logger import Logger
from PiCN.Playground.BeeSensRepo import StorageLayer, InterfaceLayer
from PiCN.Processes import PiCNSyncDataStructFactory


class RepoStack(object):
    def __init__(self, port=9500, http_port=8080, log_level=255, encoder: BasicEncoder = NdnTlvEncoder,
                 database_path="/tmp", flush_database=False, pem_path=None):
        # debug level
        logger = Logger("Repo", log_level)

        # packet encoder
        encoder.set_log_level(log_level)
        self.encoder = encoder

        # setup data structures
        synced_data_struct_factory1 = PiCNSyncDataStructFactory()
        synced_data_struct_factory1.register("face_id_table", FaceIDDict)
        synced_data_struct_factory1.register("cs", ContentStorePersistentExact)
        synced_data_struct_factory1.create_manager()
        face_id_table = synced_data_struct_factory1.manager.face_id_table()
        storage = synced_data_struct_factory1.manager.cs(db_path=database_path + "/beesens-cs.db")
        if flush_database:
            storage.delete_all()

        # initialize layers
        self.link_layer = BasicLinkLayer([UDP4Interface(port)], face_id_table, log_level=log_level)
        self.packet_encoding_layer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.storage_layer = StorageLayer(log_level=log_level)
        self.interface_layer = InterfaceLayer(http_port=http_port, log_level=log_level, pem_path=pem_path,
                                              flush_database=flush_database)

        # setup stack
        self.stack: LayerStack = LayerStack([
            self.interface_layer,
            self.storage_layer,
            self.packet_encoding_layer,
            self.link_layer
        ])

        # pass cs to storage layer
        self.storage_layer.storage = storage

    def start_forwarder(self):
        self.stack.start_all()

    def stop_forwarder(self):
        self.stack.stop_all()
        self.stack.close_all()

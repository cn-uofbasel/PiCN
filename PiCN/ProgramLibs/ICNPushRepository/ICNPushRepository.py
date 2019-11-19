"""A Push Repository using PiCN"""

from typing import List

from PiCN.LayerStack.LayerStack import LayerStack
from PiCN.Layers.RepositoryLayer import PushRepositoryLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer

from PiCN.Processes import PiCNSyncDataStructFactory

from PiCN.Layers.ICNLayer.ContentStore import ContentStorePersistentExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict

from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt


class ICNPushRepository(object):
    """A Push Repository using PiCN"""

    def __init__(self, database_path, port=9000, log_level=255, encoder: BasicEncoder = None, flush_database=False):
        # debug level
        logger = Logger("PushRepo", log_level)

        # packet encoder
        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level=log_level)
            self.encoder = encoder

        # setup data structures
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStorePersistentExact)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs(db_path=database_path + "/pushrepo.db")
        if flush_database:
            cs.delete_all()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        # default interface
        interfaces = [UDP4Interface(port)]
        mgmt_port = interfaces[0].get_port()

        # initialize layers
        self.linklayer = BasicLinkLayer(interfaces, faceidtable, log_level=log_level)
        self.packetencodinglayer = BasicPacketEncodingLayer(self.encoder, log_level=log_level)
        self.repolayer = PushRepositoryLayer(log_level=log_level)

        self.lstack: LayerStack = LayerStack([
            self.repolayer,
            self.packetencodinglayer,
            self.linklayer
        ])

        self.repolayer.cs = cs

        # mgmt
        self.mgmt = Mgmt(cs, None, None, self.linklayer, mgmt_port, self.stop_forwarder,
                         log_level=log_level)

    def start_forwarder(self):
        # start processes
        self.lstack.start_all()
        self.mgmt.start_process()

    def stop_forwarder(self):
        # Stop processes
        self.lstack.stop_all()
        # close queues file descriptors
        if self.mgmt.process:
            self.mgmt.stop_process()
        self.lstack.close_all()

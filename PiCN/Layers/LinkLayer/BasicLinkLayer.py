"""Default Link Layer implementation for PiCN"""
import multiprocessing

from PiCN.Processes import LayerProcess

from PiCN.Layers.LinkLayer.Interfaces import BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable


class BasicLinkLayer(LayerProcess):
    """Default Link Layer implementation for PiCN
    :param interface: preconfigured interface used to start the link layer
    :param faceidtable: faceidtable, that maintains the mapping between IDs and Interfaces
    """

    def __init__(self, interface: BaseInterface, faceidtable: BaseFaceIDTable):
        self.interfaces = []
        self.interfaces.append(interface)
        self.faeidtable = faceidtable

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        raise Exception("Link Layer interacts with sockets. There is no lower layer!")

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass

    def _run_poll(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                  to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        super()._run_poll(from_lower, from_higher, to_lower, to_higher)

    def _run_select(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                    to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        super()._run_select(from_lower, from_higher, to_lower, to_higher)

    def _run_sleep(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        super()._run_sleep(from_lower, from_higher, to_lower, to_higher)



import unittest.mock
import multiprocessing

from typing import Dict, Tuple, Union

from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Name, Content, Nack


class MockSocket(object):

    def __init__(self):
        self.setsockopt = unittest.mock.Mock()


class MockLinkLayer(UDP4LinkLayer):

    # noinspection PyMissingConstructor
    # super constructor not called, as no actual socket should be instantiated.
    def __init__(self, port: int = 9000):
        self._id_gen = 0
        self._ip_to_fid: Dict[Tuple[str, int], int] = {}
        self._port = port
        self.sock = MockSocket()
        self.get_or_create_fid = unittest.mock.Mock(side_effect=self._get_or_create_fid)

    def get_port(self):
        return self._port

    # noinspection PyUnusedLocal
    def _get_or_create_fid(self, addr, static: bool = False):
        if addr in self._ip_to_fid:
            return self._ip_to_fid[addr]
        fid = self._id_gen
        self._id_gen += 1
        self._ip_to_fid[addr] = fid
        return fid


class MockRepository(BaseRepository):

    def __init__(self, prefix: Name):
        manager = multiprocessing.Manager()
        self.prefix: multiprocessing.Value = manager.Value(Name, prefix)
        super().__init__()

    def is_content_available(self, icnname: Name) -> bool:
        return True

    def get_content(self, icnname: Name) -> Union[Content, Nack]:
        return Content(icnname, '')

    def set_prefix(self, prefix: Name):
        self.prefix.value = prefix

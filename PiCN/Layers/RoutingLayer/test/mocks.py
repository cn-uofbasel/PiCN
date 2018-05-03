
import unittest.mock
import multiprocessing

from typing import Dict, Tuple

from PiCN.Layers.LinkLayer import UDP4LinkLayer


class MockSocket(object):

    def __init__(self):
        self.setsockopt = unittest.mock.Mock()
        self.close = unittest.mock.Mock()


class MockLinkLayer(UDP4LinkLayer):

    # noinspection PyMissingConstructor
    # super constructor not called, as no actual socket should be instantiated.
    def __init__(self, port: int = 9000):
        manager = multiprocessing.Manager()
        self._id_gen = 0
        self._ip_to_fid: Dict[Tuple[str, int], int] = manager.dict()
        self._port = port
        self.get_or_create_fid = unittest.mock.Mock(side_effect=self._get_or_create_fid)
        self.sock = MockSocket()

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

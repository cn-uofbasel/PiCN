"""Abstract Encoder for the BasicPacketEncoding Layer"""

import abc

from PiCN.Logger import Logger
from PiCN.Packets import Packet


class BasicEncoder(object):
    """Abstract Encoder for the BasicPacketEncoding Layer"""

    @abc.abstractmethod
    def __init__(self, logger_name="BasicEncoder", log_level=255):
        self.__logger_name = logger_name
        self.__log_level = log_level
        self.logger = Logger(self.__logger_name, self.__log_level)

    def set_log_level(self, log_level):
        self.logger.setLevel(log_level)

    @abc.abstractclassmethod
    def encode(self, packet: Packet):
        """encode a packet to wireformat"""

    @abc.abstractclassmethod
    def decode(self, wire_data) -> Packet:
        """decode a packet to Packet data structure"""

    def __getstate__(self):
        d = dict(self.__dict__)
        if 'logger' in d:
            del d['logger']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)  # need to store logger parameter and recreate logger here, since it cannot be pickled
        self.logger = Logger(self.__logger_name, self.__log_level)

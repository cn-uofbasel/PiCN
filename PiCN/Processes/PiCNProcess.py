"""Abstract Process for PiCN"""

import abc
import multiprocessing

from PiCN.Logger import Logger


class PiCNProcess(object):
    """Abstract Process for PiCN"""

    def __init__(self, logger_name="PiCNProcess", log_level=255):
        self._process: multiprocessing.Process = None
        self.logger = Logger(logger_name, log_level)
        self.__logger_name = logger_name
        self.__log_level = log_level

    @abc.abstractmethod
    def start_process(self):
        """Init and start the process"""

    @abc.abstractmethod
    def stop_process(self):
        """Stop the process"""

    @property
    def process(self):
        """process instance"""
        return self._process

    @process.setter
    def process(self, process):
        self._process = process

    def __getstate__(self):
        d = dict(self.__dict__)
        if 'logger' in d:
            del d['logger']
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)  # need to store logger parameter and recreate logger here, since it cannot be pickled
        self.logger = Logger(self.__logger_name, self.__log_level)

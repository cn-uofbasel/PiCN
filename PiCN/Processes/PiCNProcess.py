"""Abstract Process for PiCN"""

import abc
import multiprocessing

from PiCN.Logger import Logger

class PiCNProcess(object):
    """Abstract Process for PiCN"""

    def __init__(self, logger_name="PiCNProcess", log_level=255):
        self._process: multiprocessing.Process = None
        self.logger = Logger(logger_name, log_level)

    @abc.abstractclassmethod
    def start_process(self):
        """Init and start the process"""

    @abc.abstractclassmethod
    def stop_process(self):
        """Stop the process"""

    @property
    def process(self):
        """process instance"""
        return self._process

    @process.setter
    def process(self, process):
        self._process = process

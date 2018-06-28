import multiprocessing

from PiCN.Processes import LayerProcess


class PinnedComputationLayer(LayerProcess):
    def __init__(self, log_level=255):
        super().__init__(logger_name="RepoLayer", log_level=log_level)
        self.storage = None

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass # this is already the highest layer.

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass # TODO


    def ageing(self):
        pass  # data should not be removed from cache

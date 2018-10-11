"""This is the BasicThunk layer used to check if it is possible to compute a result, and determine the
cost of computing the result"""
import multiprocessing

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack

class BasicThunkLayer(LayerProcess):

    def __init__(self, log_level=255):
        super().__init__("ThunkLayer", log_level)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        packet_id = data[0]
        packet = data[1]

        if isinstance(packet, Interest):
            self.handleInterest(packet_id, packet)
        elif isinstance(packet, Content):
            self.handleContent(packet_id, packet)
        elif isinstance(packet, Nack):
            self.handleNack(packet_id, packet)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        to_lower.put(data)
        return

    def handleInterest(self, id: int, interest: Interest):
        if len(interest.name.components) < 2 or interest.name.components[-2] != b"THUNK":
            self.queue_to_higher.put([id, interest])
            return

        if interest.name.components != b"NFN":
            self.queue_to_higher.put([id, interest])
            return
        #TODO parse interest -> ast
        #TODO create possible requests
        #TODO find cheapest cost, cache plans

    def handleContent(self, id: int, content: Content):
        pass

    def handleNack(self, id: int, nack: Nack):
        pass
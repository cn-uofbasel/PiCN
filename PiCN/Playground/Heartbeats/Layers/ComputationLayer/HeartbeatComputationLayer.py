import multiprocessing
import threading
from math import pow
import time

from PiCN.Processes import LayerProcess
from PiCN.Packets import Name, Interest, Content, Nack, NackReason
from PiCN.Playground.Heartbeats.Layers.PacketEncoding.Heartbeat import Heartbeat


class HeartbeatComputationLayer(LayerProcess):
    def __init__(self, log_level=255):
        super().__init__(logger_name="HeartbeatNFNLayer", log_level=log_level)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass  # this is already the highest layer.

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info("Received packet")
        packet_id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            self.logger.info("Received packet is an interest")
            self.handleInterest(packet_id, packet)
        else:
            self.logger.info("Received packet is not an interest")
            return

    def return_result(self, packet_id, content: Content):
        self.queue_to_lower.put([packet_id, content])

    def return_nack(self, packet_id, interest: Interest):
        self.queue_to_lower.put([packet_id, Nack(interest.name, reason=NackReason.NOT_SET,
                                                 interest=interest)])  # TODO -- choose an appropriate NACK reason

    def handleInterest(self, packet_id: int, interest: Interest):

        components = interest.name.components
        if components[-1] == b"hNFN":
            try:
                num_params = int(components[-2])
                self.params = components[-num_params - 2:-2]
                self.params = list(map(lambda x: x.decode('utf-8'), self.params))
                assert (num_params < len(interest.name.components) - 2)
                self.function_name = components[:-num_params - 2]
                self.function_name = "/" + "/".join(list(map(lambda x: x.decode('utf-8'), self.function_name)))

            except:
                self.return_nack(packet_id, interest)
                self.logger.info("Invalid computation expression. Return NACK.")
                return

            if self.function_name == "/the/prefix/square":
                # start thread to do computation
                arguments = [packet_id, self.pinned_function_square, self.params, interest.name]
                t = threading.Thread(target=self.executePinnedFunction, args=arguments)
                t.setDaemon(True)
                t.start()
                # start thread to send heartbeat
                # -- TODO (here?)
                return
            else:
                self.return_nack(packet_id, interest)
                self.logger.info("Pinned function not available. Return NACK.")
            return
        else:
            self.logger.info("Received interest does not contain a computation expression")
        return

    def heartbeat(self, packet_id, name, interval, stop_event):
        """
        Send a periodic heartbeat
        :param packet_id: Packet ID of original interest
        :param name: Name of original interest
        :param interval: Heartbeat interval (seconds)
        :return:
        """
        while not stop_event.is_set():
            self.logger.info("Send heartbeat for: " + name.to_string())
            self.queue_to_lower.put([packet_id, Heartbeat(name)])
            time.sleep(interval)

    ### defining some pinned functions

    def executePinnedFunction(self, packet_id, function, params, interest_name: Name):
        # start heartbeat
        self.logger.info("Start heartbeat for: " + interest_name.to_string())
        heartbeat_interval = 2
        stop_heartbeat_event = threading.Event()
        arguments = [packet_id, interest_name, heartbeat_interval, stop_heartbeat_event]
        t = threading.Thread(target=self.heartbeat, args=arguments)
        t.setDaemon(True)
        t.start()
        # start computation
        self.logger.info("Start computation for: " + interest_name.to_string())
        result = function(params)
        content_object = Content(interest_name, str(result))
        # return result and stop heartbeat
        self.queue_to_lower.put([packet_id, content_object])
        stop_heartbeat_event.set()
        self.logger.info("Return result for: " + interest_name.to_string())

    def pinned_function_square(self, params):
        # TODO -- check if params contains valid parameters
        time.sleep(10)
        return int(pow(int(params[0]), 2))

    def ageing(self):
        pass  # ageing not necessary

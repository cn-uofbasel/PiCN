"""NFN Layer Implementation, containing the NFN Dispatcher
    Queues to Computation ship only the packet, no ID
    Queues to lower layer ship ID and packet
"""

import multiprocessing
import threading
import time
from typing import List, Dict

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Name

from PiCN.Layers.NFNLayer.NFNEvaluator import NFNEvaluator

class BasicNFNLayer(LayerProcess):
    """NFN Layer Implementation"""

    def __init__(self, logger_name="PiCNProcess", debug_level=255):
        super().__init__("NFN Layer", debug_level)
        self._running_computations: Dict[int, NFNEvaluator] = {} #computation id --> computation
        self._computation_request_table: Dict[Name, List[int]] = {}  # request(name) --> [computation id]
        self._pending_computations: multiprocessing.Queue[Interest] = multiprocessing.Queue()
        self._max_running_computations: int = 50
        self._next_computation_id: int = 0
        self._ageing_interval: int = 4
        self._timeout_interal: int = 20
        self.nfn_evaluator_type = type(NFNEvaluator)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        id = data[0]
        packet = data[1]
        if isinstance(packet, Interest):
            if len(packet.name.components) > 2 and packet.name.components[-3] == "R2C":
                self.handle_R2C_interest(packet)
            else:
                self.add_computation(packet)
        elif isinstance(packet, Content):
            if len(packet.name.components) > 2 and packet.name.components[-3] == "R2C":
                self.handle_R2C_content(packet)
            else:
                if not packet.name in self._computation_request_table:
                    return
                cids = self._computation_request_table[packet.name]
                for cid in cids:
                    self._running_computations[cid].start_time = time.time()
                    self._running_computations[cid].computation_in_queue.put(data)
                del self._computation_request_table[packet.name]

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """empty since there is no higher layer"""
        pass

    def ageing(self):
        """perform the aging operations for the NFN Layer
           perfom the timeout prevention
           """
        try:
            self.logger.debug("Ageing NFN")

            self.handle_computation_queue()
            self.handle_computation_timeouts()
            self.run_computation()

            t = threading.Timer(self._ageing_interval, self.ageing)
            t.setDaemon(True)
            t.start()
        except:
            pass
        pass

    def add_computation(self, interest: Interest):
        """add a computation to the list of pending computations"""
        self._pending_computations.put(interest)

    def handle_computation_queue(self):
        """check the computation queues """
        for cid in self._running_computations:
            comp = self._running_computationsp[cid]
            while not comp.computation_out_queue.empty():
                packet = comp.computation_out_queue.get()
                if isinstance(packet, Interest):
                    if(packet.name in self._computation_request_table):
                        self._computation_request_table[packet.name].append(cid)
                    else:
                        self._computation_request_table[packet.name] = [cid]
                    self.queue_to_lower.put([cid, packet])
                elif isinstance(packet, Content):
                    self.queue_to_lower.pit([cid, packet])
                    self.stop_computation(cid)
                    return

    def stop_computation(self, cid: int):
        """Stop a running computation"""
        self._running_computations[cid].stop_process()
        del self._running_computations[cid]

    def handle_computation_timeouts(self):
        """handle the timeouts of the computation"""
        #todo
        pass

    def run_computation(self):
        """execute a computation if there are capacities"""
        num_running_computations = len(self._running_computations)
        if(num_running_computations > self._max_running_computations):
            return
        else:
            while(len(self._running_computations) < self._max_running_computations
                  and not self._pending_computations.empty()):
                interest = self.queue_to_higher.get()
                evaluator = self.nfn_evaluator_type(interest)
                self._running_computations[self._next_computation_id] = evaluator
                self._next_computation_id = self._next_computation_id + 1
                evaluator.start_process()

    def request_data(self, computation_id):
        """request data for a computation"""
        #TODO
        pass

    def handle_R2C_interest(self, interest: Interest):
        """Handle the R2C Mesasges Content"""
        if interest.name not in self._computation_request_table:
            return
        cid = self._computation_request_table[interest.name]
        if interest.name.components[-2] == "STOP":
            #TODO , check no one else awaits result
            self.stop_computation(cid)
            #TODO , send reply message
        pass

    def handle_R2C_content(self, content: Content):
        """Handle the R2C Mesasges Content"""
        #TODO handle r2c content
        pass

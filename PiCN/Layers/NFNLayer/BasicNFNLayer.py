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
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable

from PiCN.Layers.NFNLayer.NFNEvaluator import NFNEvaluator

class BasicNFNLayer(LayerProcess):
    """NFN Layer Implementation"""

    def __init__(self, manager: multiprocessing.Manager, content_store: BaseContentStore,
                 fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 logger_name="NFN Layer", debug_level=255):
        super().__init__(logger_name, debug_level)
        self.manager = manager
        self.content_store = content_store
        self.fib = fib
        self.pit = pit
        self._running_computations: Dict[int, NFNEvaluator] = {} #computation id -> computation
        self._computation_request_table: Dict[Name, List[int]] = {}  # request(name) -> [computation id]
        self._pending_computations: multiprocessing.Queue[Interest] = multiprocessing.Queue()
        self.rewrite_table: Dict[Name, List[Name]] = self.manager.dict() #rewritten name -> original name

        self._max_running_computations: int = 50
        self._next_computation_id: int = 0
        self._ageing_interval: int = 2
        self._timeout_interal: int = 20

        self.nfn_evaluator_type = NFNEvaluator

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
                if packet.name in self.rewrite_table:
                    self.handle_rewrite_table(packet)
                if packet.name in self._computation_request_table:
                    self.handle_compuation_request_table(packet)

    def handle_compuation_request_table(self, packet):
        """handle computation request table entries"""
        cids = self._computation_request_table[packet.name]
        for cid in cids:
            self._running_computations[cid].start_time = time.time()
            self._running_computations[cid].computation_in_queue.put(packet)
        del self._computation_request_table[packet.name]

    def handle_rewrite_table(self, packet):
        """handle computation request table entries"""
        original_names = self.rewrite_table[packet.name]
        for on in original_names:
            cid = 0
            content = Content(on, packet.content)
            self.queue_to_lower.put([cid, content])
        #stop computation
        waiting_comp_ids =  self._computation_request_table[packet.name]
        remove_ids = []
        for cid in waiting_comp_ids:
            if self._running_computationsp[cid].interest.name == packet.name:
                self._running_computations[cid].stop_process()
                remove_ids.append(cid)
        for cid in remove_ids:
            del self._running_computations[cid]


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
            comp = self._running_computations[cid]
            while not comp.computation_out_queue.empty():
                packet = comp.computation_out_queue.get()
                if isinstance(packet, List): #Rewritten packet
                    if packet[0].name in self.rewrite_table:
                        self.queue_to_lower.put(packet[0])
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
            while((not self._pending_computations.empty())
                  and len(self._running_computations) < self._max_running_computations):
                interest = self._pending_computations.get()
                evaluator = self.nfn_evaluator_type(interest, self.content_store, self.fib, self.pit, self.rewrite_table)
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

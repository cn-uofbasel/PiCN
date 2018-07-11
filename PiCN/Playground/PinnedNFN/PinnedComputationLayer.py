import multiprocessing
import threading
from math import pow
import time
from PiCN.Processes import LayerProcess
from PiCN.Packets import Name, Interest, Content, Nack, NackReason
import threading

class PinnedComputationLayer(LayerProcess):

    def __init__(self, replica_id, log_level=255):
        super().__init__(logger_name="PinnedNFNLayer (" + str(replica_id) + ")", log_level=log_level)
        self.storage = None

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
        self.queue_to_lower.put([packet_id, Nack(interest.name, reason=NackReason.NOT_SET, interest=interest)])  # TODO -- choose an appropriate NACK reason

    def handleInterest (self, packet_id: int, interest: Interest):

        components = interest.name.components
        if components[-1] == b"pNFN":
            try:
                num_params = int(components[-2])
                self.params = components[-num_params - 2:-2]
                self.params = list(map(lambda x: x.decode('utf-8'), self.params))
                assert(num_params < len(interest.name.components)-2)
                self.function_name = components[:-num_params - 2]
                self.function_name = "/" + "/".join(list(map(lambda x: x.decode('utf-8'), self.function_name)))

            except:
                self.return_nack(packet_id, interest)
                self.logger.info("Invalid computation expression. Return NACK.")
                return

            if self.function_name == "/the/prefix/square":
                self.return_result(packet_id, Content(interest.name, "5"))  # QUESTION -- return as string?
                self.logger.info("Result returned")
                #self.result = self.pinned_function_square(self.params)
                #run the computation in a thread
                arguments = [self.pinned_function_square, self.params, interest.name]
                t = threading.Thread(target=self.executePinnedFunction, args=arguments)
                t.setDaemon(True)
                t.start()
                return
            else:
               self.return_nack(packet_id, interest)
               self.logger.info("Pinned function not available. Return NACK.")
            return
        if components[-1] == b"resultpNFN":
            try:
                num_parameters = int(components[-2])
                parameters = components[-num_parameters - 2:-2]
                parameters = list(map(lambda x: x.decode('utf-8'), parameters))
                assert(num_parameters < len(interest.name.components)-2)
                func_name = components[:-num_parameters - 2]
                func_name = "/" + "/".join(list(map(lambda x: x.decode('utf-8'), func_name)))

            except:
                self.return_nack(packet_id, interest)
                self.logger.info("Invalid computation expression. Return NACK.")
                return


            if func_name == self.function_name and parameters == self.params:
                self.return_result(packet_id, Content(interest.name, "empty"))
                return
            #if function_name == "/the/prefix/squareresult" and parameters == self.params:
               # self.return_result(packet_id, Content(interest.name, str(self.result)))
                #return
            else:
                self.return_nack(packet_id, interest)
                self.logger.info("Pinned function is not computed yet. Return NACK.")
                return

        # elif components[-1] == b"resultpNFN":
        #     try:
        #         func_name = components[:-1]
        #         func_name = "/" + "/".join(list(map(lambda x: x.decode('utf-8'), func_name)))
        #     except:
        #         self.return_nack(packet_id, interest)
        #         self.logger.info("Invalid computation expression. Return NACK.")
        #         return


        else:
            self.logger.info("Received interest does not contain a computation expression")
        return

    # defining some pinned functions

    def executePinnedFunction(self, function, params, interest_name: Name):
        result = function(params)
        new_components = interest_name.to_string().split("/")[1:-1]
        new_components.append("resultpNFN")
        new_name = "/" + '/'.join(new_components)
        content_object = Content(new_name, str(result))
        self.queue_to_lower.put([-1, content_object])

    def pinned_function_square(self,params):
        # TODO -- check if params contains valid parameters
        time.sleep(5)
        return int(pow(int(params[0]), 2))

    def ageing(self):
        pass  # ageing not necessary

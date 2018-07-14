"""Data Structure for managing LayerProcesses and their queues"""

import multiprocessing
from typing import List

from PiCN.Processes import LayerProcess


class LayerStack(object):
    """
    Data structure for managing LayerProcesses and their queues
    """

    def __init__(self, layers: List[LayerProcess]):
        """
        Create a layer stack from a list of layers, where the topmost layer is the first element in the list.
        :param layers: List of layers to stack onto each other.
        """
        self.layers: List[LayerProcess] = []
        self.queues: List[multiprocessing.Queue] = []
        self._queue_to_higher = multiprocessing.Queue()
        self._queue_from_higher = multiprocessing.Queue()
        self._queue_to_lower = multiprocessing.Queue()
        self._queue_from_lower = multiprocessing.Queue()
        self.__started = False
        if len(layers) == 0:
            raise ValueError('Can\'t have an empty LayerStack')
        # Setup queues for each pair of layers
        for i in range(len(layers) - 1):
            upper = layers[i]
            lower = layers[i + 1]
            # Create two queues for communication
            q_to_upper = multiprocessing.Queue()
            q_to_lower = multiprocessing.Queue()
            upper.queue_to_lower = q_to_lower
            upper.queue_from_lower = q_to_upper
            lower.queue_to_higher = q_to_upper
            lower.queue_from_higher = q_to_lower
            # Append layers and queues to resource lists
            self.layers.append(upper)
            self.queues.append(q_to_upper)
            self.queues.append(q_to_lower)
        # Append last layer to resource list
        self.layers.append(layers[len(layers) - 1])
        self.layers[0].queue_to_higher = self.queue_to_higher
        self.layers[0].queue_from_higher = self.queue_from_higher
        self.layers[len(self.layers) - 1].queue_to_lower = self.queue_to_lower
        self.layers[len(self.layers) - 1].queue_from_lower = self.queue_from_lower

    def insert(self, layer: LayerProcess, on_top_of: LayerProcess = None, below_of: LayerProcess = None):
        """
        Insert a layer into the layer stack, placing it on top of or beneath another layer. Either on_top_of or below_of
        must be provided.
        :param layer: The layer to insert.
        :param on_top_of: The layer on top of which the new layer should be inserted. Must not be used together with
                          below_of.
        :param below_of: The layer beneath of which the new layer should be inserted. Must not be used together with
                          on_top_of.
        :raises multiprocessing.ProcessError if this method is called after the layer stack was started.
        :raises TypeError if the layer to insert is None, or on_top_of and below_of are used together.
        :raises ValueError if on_top_of/below_of is not a layer in this LayerStack.
        """
        if self.__started:
            raise multiprocessing.ProcessError('LayerStack should not be changed after its processes were started.')
        if layer is None:
            raise TypeError('Layer is None.')
        # Make sure that exactly one out of on_top_of, below_of is provided.
        if (on_top_of is None) == (below_of is None):
            raise TypeError('Needs either on_top_of xor below_of')
        insert_above: bool = on_top_of is not None
        ref_layer = on_top_of if insert_above else below_of
        # Find position of the reference layer
        for i in range(len(self.layers)):
            if self.layers[i] == ref_layer:
                # If the new layer should be inserted above the reference layer, it should be placed at the current
                # position of the reflayer, pushing the reflayer and following down by one. Else the reflayer should
                # remain at its position, only subsequent layers should be pushed down by one.
                if insert_above:
                    self.__insert(layer, i)
                else:
                    self.__insert(layer, i + 1)
                return
        raise ValueError('Reference layer is not in the layer stack.')

    def close_all(self):
        """
        Utility function to close all queues managed by the LayerStack.
        """
        [q.close() for q in self.queues]
        self._queue_to_higher.close()
        self._queue_from_higher.close()
        self._queue_to_lower.close()
        self._queue_from_lower.close()

    def start_all(self):
        """
        Utility function to start all LayerProcesses managed by the LayerStack.
        """
        self.__started = True
        [l.start_process() for l in self.layers]

    def stop_all(self):
        """
        Utility function to stop all LayerProcesses managed by the LayerStack.
        """
        [l.stop_process() for l in self.layers]

    @property
    def queue_to_higher(self):
        return self._queue_to_higher

    @queue_to_higher.setter
    def queue_to_higher(self, queue: multiprocessing.Queue):
        if self.__started:
            raise multiprocessing.ProcessError('LayerStack should not be changed after its processes were started.')
        self.queue_to_higher = queue
        self.layers[0].queue_to_higher = queue

    @property
    def queue_from_higher(self):
        return self._queue_from_higher

    @queue_from_higher.setter
    def queue_from_higher(self, queue: multiprocessing.Queue):
        if self.__started:
            raise multiprocessing.ProcessError('LayerStack should not be changed after its processes were started.')
        self.queue_from_higher = queue
        self.layers[0].queue_from_higher = queue

    @property
    def queue_to_lower(self):
        return self._queue_to_lower

    @queue_to_lower.setter
    def queue_to_lower(self, queue: multiprocessing.Queue):
        if self.__started:
            raise multiprocessing.ProcessError('LayerStack should not be changed after its processes were started.')
        self.queue_to_lower = queue
        self.layers[len(self.layers) - 1].queue_to_lower = queue

    @property
    def queue_from_lower(self):
        return self._queue_from_lower

    @queue_from_lower.setter
    def queue_from_lower(self, queue: multiprocessing.Queue):
        if self.__started:
            raise multiprocessing.ProcessError('LayerStack should not be changed after its processes were started.')
        self.queue_from_lower = queue
        self.layers[len(self.layers) - 1].queue_from_lower = queue

    def __insert(self, layer: LayerProcess, at: int):
        # Get the layers between which to insert the new layer
        layer_above = self.layers[at - 1] if at > 0 else None
        layer_below = self.layers[at] if at < len(self.layers) else None
        queues: List[multiprocessing.Queue] = []
        # If both layers exist, reuse the queues between them
        if layer_above is not None and layer_below is not None:
            queues.append(layer_above.queue_to_lower)
            queues.append(layer_above.queue_from_lower)
        # Create two new queues needed for connecting the new layer to the stack.
        for x in range(2):
            q = multiprocessing.Queue()
            self.queues.append(q)
            queues.append(q)
        # Set up queues to the layer above
        if layer_above is not None:
            q_up = queues.pop()
            q_down = queues.pop()
            layer_above.queue_to_lower = q_down
            layer_above.queue_from_lower = q_up
            layer.queue_to_higher = q_up
            layer.queue_from_higher = q_down
        # Set up queues to the layer below
        if layer_below is not None:
            q_up = queues.pop()
            q_down = queues.pop()
            layer.queue_to_lower = q_down
            layer.queue_from_lower = q_up
            layer_below.queue_to_higher = q_up
            layer_below.queue_from_higher = q_down
        # Insert the new layer at the wanted position
        self.layers.insert(at, layer)
        self.layers[0].queue_to_higher = self.queue_to_higher
        self.layers[0].queue_from_higher = self.queue_from_higher
        self.layers[len(self.layers) - 1].queue_to_lower = self.queue_to_lower
        self.layers[len(self.layers) - 1].queue_from_lower = self.queue_from_lower

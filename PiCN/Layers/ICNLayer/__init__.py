"""ICN Forwarding Plane. Maintains data structures for ICN Forwarding
    * queue from lower is expected to deliver [face id, Packets.Packet]
    * queue from higher is expected to deliver [highlevelid, Packets.Packet]
    * queue to lower expects [face id, Packets.Packet]
    * queue to higher expects [highlevelid, Packets.Packet]
    highlevelid on the queues to higher and from higher is a number ,
    that can be used to dispatch packets on the higher layer
"""

from .BaseICNDataStruct import BaseICNDataStruct
from .BasicICNLayer import BasicICNLayer

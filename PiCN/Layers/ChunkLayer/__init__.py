""" Chunk Layer, splitting a packet to
several packets and a meta data file or
reassable all chunks to a packet
    * to_lower expects a chunk of a packet [0, packet]
    * to_higher expects a packet [0, packet]
    * from_lower expects a chunk of a packet [0, packet]
    * from_higher expects a packet [0, packet]

the data structure of a chunk is the same as of a packet,
but has a limited size.

The name must not be chunked, while the name payload can be chunked.
"""

from .BasicChunkLayer import BasicChunkLayer
from .BasicChunkLayer import RequestTableEntry
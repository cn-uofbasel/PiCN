""" Packet encoding Module for PiCN
    * from_lower queue expects to get [faceid, encoded_data]
    * from_higher queue expects to get [faceid, data_as_datastruct/packet]
    * to_lower queue has to contain [faceid, encoded_data]
    * to_higher queue h to get [faceid, data_as_datastruct/packet]
    * Packet Encoder go to Encoder, should perform wire-encoding <--> packet (package: Packets)
"""

from .BasicPacketEncodingLayer import BasicPacketEncodingLayer
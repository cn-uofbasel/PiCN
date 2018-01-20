#!/usr/bin/env python3

# flic2content.py
#   implements the FLIC consumer side

# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import binascii
import copy
from   PiCN.Packets                                          import Name
from   PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import TlvDecoder
from   PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder

class DeFlic():

    def __init__(self, icn, decoder=None):
        self.icn = icn
        self.decoder = decoder
        self.NDN_TYPE_MANIFEST             = 0x990
        self.NDN_TYPE_MANIFEST_INDEXTABLE  = 0x991
        self.NDN_TYPE_MANIFEST_DATAPTR     = 0x992
        self.NDN_TYPE_MANIFEST_MANIFESTPTR = 0x993

    def _payload2table(self, data: bytes):
        pass

    def _indexTable2data(self, pfx: Name, decoder, end: int):
        # traverse the manifest tree
        # input: decoder with index table
        # output: reassembled data
        data = b''
        while decoder._offset < end:
            if decoder.peekType(self.NDN_TYPE_MANIFEST_DATAPTR, end):
                ptr = decoder.readBlobTlv(self.NDN_TYPE_MANIFEST_DATAPTR)
                # print("data ptr %s" % binascii.hexlify(ptr))
                name = copy.copy(pfx).setDigest(ptr)
                # print(name.to_json())
                chunk = self.icn.readChunk(name)
                data += NdnTlvEncoder().decode(chunk).get_bytes()
            elif decoder.peekType(self.NDN_TYPE_MANIFEST_MANIFESTPTR, end):
                ptr = decoder.readBlobTlv(self.NDN_TYPE_MANIFEST_MANIFESTPTR)
                # print("manifest ptr %s" % binascii.hexlify(ptr))
                name = copy.copy(pfx).setDigest(ptr)
                chunk = self.icn.readChunk(name)
                content = NdnTlvEncoder().decode(chunk)
                data += self.manifestToBytes(content.get_bytes())
            else:
                print("invalid index table entry")
                return data
        return data

    def manifestToBytes(self, pfx: Name, manifest: bytes):
        # input: manifest (only the payload of the chunk)
        # output: re-assembled raw e2e bytes
        decoder = TlvDecoder(manifest)
        # print("manifestToBytes: %d bytes" % len(decoder._input))
        end = decoder.readNestedTlvsStart(self.NDN_TYPE_MANIFEST)
        decoder.readNestedTlvsStart(self.NDN_TYPE_MANIFEST_INDEXTABLE)
        data = self._indexTable2data(pfx, decoder, end)
        decoder.finishNestedTlvs(end)
        return data

    def NFNresultToBytes(self, data):
        # input: byte array (containting a "NFN result TLV")
        # output: e2e raw result bytes
        pkt = self.decoder(data)
        if pkt.T == NFNdirectResult:
            return pkt.V
        # we got a manifest
        return self.manifestToBytes(pkt.V)


    # TODO:
    # def resultToStream(self, data):
    #    return DeFLIC_ITER(...)

# class DeFLIC_ITER():
#
#     def __init__(self):
#         pass

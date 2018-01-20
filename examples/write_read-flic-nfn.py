#!/usr/bin/env python3

# examples/write_read-flic-nfn.py
#
#  this is a demo of using
#  - the PiCN client lib,
#  - the FLIC extension
#  for first writing then reading NFN results, both small and
#  large (mandating manifests). The result fits in in a single
#  chunk, in both cases.
#
# (c) 2018-01-20 <christian.tschudin@unibas.ch>

import copy
import random
import sys
sys.path.append('..')
import time

from PiCN                import client
from PiCN.ProgramLibs    import flic
from PiCN.Packets        import Content, Name
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
import PiCN.client           as client
from PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import TlvEncoder, TlvDecoder

NFN_NDN_TYPE_RESULT_DIRECT        = 0x998
# NFN_NDN_TYPE_RESULT_INDIRECT      = manifest type

class NFNresult():

    def __init__(self, icn):
        self.icn = icn
        self.MTU = 4000

    def bytesToNFNresult(self, localName: Name,
                         data: bytes, 
                         forceManifest=False):
        # input: e2e result bytes, as produced by NFN execution
        # output: "NFN result TLV", either constant or indirect (=manifest)
        #         this is just the payload, not the (NDN/CCNx/...) chunk

        if len(data) < self.MTU and not forceManifest:
            # NFN direct result
            name = copy.deepcopy(icn.getRepoPrefix())
            name.__add__(localName._components)
            payload = TlvEncoder()
            payload.writeBlobTlv(NFN_NDN_TYPE_RESULT_DIRECT, data)
            c = Content(name, payload.getOutput())
            c = NdnTlvEncoder().encode(c) # and sign
            self.icn.writeChunk(name, c)
            return name, c

        # NFN indirect result
        name = copy.deepcopy(icn.getRepoPrefix())
        name.__add__(localName._components)
        name, manifest = flic.MkFlic(self.icn).bytesToManifest(name, data)
        c = Content(name, manifest)
        return name, NdnTlvEncoder().encode(c) # and sign


    def NFNresultToBytes(self, name, data: bytes) -> bytes:
        # input: byte array (containting a "NFN result TLV")
        # output: e2e raw result bytes

        decoder = TlvDecoder(data)
        if decoder.peekType(NFN_NDN_TYPE_RESULT_DIRECT, len(data)):
            return decoder.readBlobTlv(NFN_NDN_TYPE_RESULT_DIRECT)
        if decoder.peekType(flic.NDN_TYPE_MANIFEST, len(data)):
            name = copy.deepcopy(name)
            name._components.pop()
            return flic.DeFlic(self.icn)._manifestToBytes(name, data)
        return None

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    # repo must be running at localhost:9876
    icn.attach("127.0.0.1", 9876, 9876, 'ndn2013')

    data1 = bytes(random.getrandbits(8) for _ in range(1024 + 123))
    # print("len of data1 is %d bytes" % len(data1))
    data2 = bytes(random.getrandbits(8) for _ in range(5*1024 + 123))
    # print("len of data2 is %d bytes" % len(data2))

    nfnResult = NFNresult(icn)

    # store
    name = [time.strftime('%Y%m%d-%H%M%S-small'), 'c(r(a(z(y))))', 'NFN']
    name = Name(suite='ndn2013').__add__([n.encode('ascii') for n in name])
    name1, chunk1 = nfnResult.bytesToNFNresult(name, data1)
    # print("name1 %s, len(chunk1)=%d" % (name1, len(chunk1)))

    name = [time.strftime('%Y%m%d-%H%M%S-large'), 'c(r(a(z(y))))', 'NFN']
    name = Name(suite='ndn2013').__add__([n.encode('ascii') for n in name])
    name2, chunk2 = nfnResult.bytesToNFNresult(name, data2)
    # print("name2 %s, len(chunk2)=%d" % (name2, len(chunk2)))

    # retrieve (we could also use payload1, payload2, because this
    # is what a client typically would receive from a NFN request)
    chunk = icn.readChunk(name1)
    content = NdnTlvEncoder().decode(chunk)
    data1copy = nfnResult.NFNresultToBytes(name1, content.get_bytes())
    chunk = icn.readChunk(name2)
    content = NdnTlvEncoder().decode(chunk)
    name2.digest = None
    data2copy = nfnResult.NFNresultToBytes(name2, content.get_bytes())

    if not data1 or not data2:
        print("ERROR: no content received")
        raise IOError

    print("retrieved content: %d bytes" % len(data1copy))
    if data1 == data1copy:
        print("  contents match!")
    else:
        print("  contents differ :-(")
    print("retrieved content: %d bytes" % len(data2copy))
    if data2 == data2copy:
        print("  contents match!")
    else:
        print("  contents differ :-(")

    icn.detach()

# eof

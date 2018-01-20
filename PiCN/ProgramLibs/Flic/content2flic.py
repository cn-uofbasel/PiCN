#!/usr/bin/env python3

# content2flic.py
#   implements the FLIC producer side

# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import copy
import hashlib
import PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder        as ndn_enc
import PiCNExternal.pyndn.encoding.tlv.tlv.tlv                as ndn_const
from   PiCN.Packets                                       import Content
from   PiCN.Layers.PacketEncodingLayer.Encoder            import NdnTlvEncoder
from   PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import TlvEncoder
from   PiCN.Packets.Name import Name

class MkFlic():

    def __init__(self, icn, MTU=4000):
        self.icn = icn
        # self.encoder = ndn_encoder.TlvEncoder()
        self.MTU = MTU
        self.NDN_TYPE_MANIFEST             = 0x990
        self.NDN_TYPE_MANIFEST_INDEXTABLE  = 0x991
        self.NDN_TYPE_MANIFEST_DATAPTR     = 0x992
        self.NDN_TYPE_MANIFEST_MANIFESTPTR = 0x993

    def _mkContentChunk(self, name: Name, data: bytes):
        # input: name, payload bytes
        # output: chunk bytes
        c = Content(name, data)
        ndn = NdnTlvEncoder()
        return ndn.encode(c) # and sign

    def bytesToManifest(self, name: Name, data: bytes):
        # input: byte array
        # output: (nameOfRootManifest, rootManifestChunk)

        # cut content in pieces
        raw = []
        while len(data) > 0:
            raw.append(data[:self.MTU])
            data = data[self.MTU:]

        # persist pieces and learn their hash pointers
        ptrs = []
        for r in raw:
            chunk = self._mkContentChunk(name, r)
            self.icn.writeChunk(name, chunk)
            h = hashlib.sha256()
            h.update(chunk)
            ptrs.append(h.digest())
            # n = copy.copy(name)
            # n.__add__([h.digest])
            # ptrs.append(n.as_bytes())

        # create list of index tables, the M pointers will be added later
        # -> DDDDDDM -> DDDDDM -> ...
        tables = []
        while len(ptrs) > 0:
            tbl = b'' # index table
            while len(ptrs) > 0:
                # add an entry to the index table
                e = TlvEncoder()
                e.writeBlobTlv(self.NDN_TYPE_MANIFEST_DATAPTR, ptrs[0])
                e = e.getOutput().tobytes()
                # collect pointers as long as the manifest fits in a chunk
                if len(tbl) + len(e) + 100 > self.MTU:
                    break
                tbl += e
                ptrs = ptrs[1:]
            tables.append(tbl)

        # persist the manifests, start at the end, add the M pointers
        tailPtr = None
        while len(tables) > 0:
            tbl = tables[-1]
            if tailPtr:
                e = TlvEncoder()
                e.writeBlobTlv(self.MANIFEST_MANIFESTPTR, tailPtr)
                tbl += e.getOutput()
            m = TlvEncoder()
            m.writeBlobTlv(self.NDN_TYPE_MANIFEST_INDEXTABLE, tbl)
            m.writeTypeAndLength(self.NDN_TYPE_MANIFEST, len(m))
            c = Content(name, m.getOutput())
            ndn = NdnTlvEncoder()
            chunk = ndn.encode(c) # and sign
            if len(tables) == 1:
                name = copy.copy(name)
                name.__add__([b'_'])
            self.icn.writeChunk(name, chunk)
            h = hashlib.sha256()
            h.update(chunk)
            tailPtr = h.digest()
            tables = tables[:-1]

        return (name, chunk)

    # this method should move to some NFN module
    def bytesToNFNresult(self, localName: Name, data: bytes, 
                         forceManifest=False):
        # input: e2e result bytes, as produced by NFN execution
        # output: "NFN result TLV", either constant or indirect (=manifest)

        n = copy.copy(icn.getRepoPrefix())
        n.__add__(localName._components)
        localName = n
        if len(data) < self.MTU and not forceManifest:
            # NFN direct result
            payload = TlvEncoder()
            payload.writeBlobTlv(self.NFN_DIRECT_RESULT, data)
            c = Content(localName, payload.getOutput())
            ndn = NdnTlvEncoder()
            return ndn.encode(c) # and sign

        # NFN indirect result
        name, manifest = self.bytesToManifest(localName, data)
        payload = TlvEncoder()
        payload.writeBlobTlv(self.NFN_INDIRECT_RESULT, manifest)
        c = Content(name, payload.getOutput())
        ndn = NdnTlvEncoder()
        return ndn.encode(c) # and sign

# eof

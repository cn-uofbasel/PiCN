#!/usr/bin/env python3

# content2flic.py
#   implements the FLIC producer side

# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import copy
import hashlib
import PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder          as ndn_enc
import PiCNExternal.pyndn.encoding.tlv.tlv.tlv                  as ndn_const
import PiCN.Packets.Content                                     as picn_content
import PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder.py as picn_ndn_enc
from   PiCN.Packets.Name import Name

class FLICer():

    def __init__(self, repo, MTU=4000):
        self.repo = repo
        # self.encoder = ndn_encoder.TlvEncoder()
        self.MTU = MTU
        self.NDN_TYPE_MANIFEST             = 0x990
        self.NDN_TYPE_MANIFEST_INDEXTABLE  = 0x991
        self.NDN_TYPE_MANIFEST_DATAPTR     = 0x992
        self.NDN_TYPE_MANIFEST_MANIFESTPTR = 0x993

    def _mkContentChunk(self, name: Name, data: bytes):
        # input: name, payload bytes
        # output: chunk bytes
        c = picn_content(name, data)
        pkt = picn_ndn_enc.NdnTlvEncoder()
        return pkt.encode(c) # and sign

    def bytesToManifest(self, name: Name, data: bytes):
        # input: byte array
        # output: (nameOfRootManifest, rootManifestChunk)

        # cut content in pieces
        raw = []
        while len(data) > 0:
            raw.append(data[:MTU])
            data = data[MTU:]

        # persist pieces and learn their hash pointers
        ptrs = []
        for r in raw:
            chunk = self._mkContentChunk(name, r)
            h = hashlib.sha1()
            h.update(chunk)
            n = copy.copy(name)
            n.__add__(h.digest)
            ptrs.append(n.as_bytes())
            self.repo.write(name, chunk)

        # create list of index tables, the M pointers will be added later
        # -> DDDDDDM -> DDDDDM -> ...
        tables = []
        while len(ptrs) > 0:
            tbl = '' # index table
            while len(ptrs) > 0:
                # add an entry to the index table
                e = ndn_enc.TlvEncoder()
                e.writeBlobTlv(self.MANIFEST_DATAPTR, ptrs[0])
                e = e.getOutput()
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
                e = ndn_enc.TlvEncoder()
                e.writeBlobTlv(self.MANIFEST_MANIFESTPTR, tailPtr)
                tbl += e.getOutput()
            m = ndn_enc.TlvEncoder()
            m.writeBlobTlv(self.MANIFEST_INDEXTABLE, tbl)
            c = picn_content(name, m.getOutput())
            pkt = picn_ndn_enc.NdnTlvEncoder()
            chunk = pkt.encode(c) # and sign
            if len(tables) == 1:
                name = copy.copy(name)
                name.__add__('_')
            self.repo.write(name, chunk)
            h = hashlib.sha1()
            h.update(chunk)
            tailPtr = h.digest()
            tables = tables[:-1]

        return (name, chunk)

    def bytesToNFNresult(self, localName: Name, data: bytes, 
                         forceManifest=False):
        # input: e2e result bytes, as produced by NFN execution
        # output: "NFN result TLV", either constant or indirect (=manifest)

        n = copy.copy(repo.getDefaultPrefix())
        n.__add__(localName._components)
        localName = n
        if len(data) < self.MTU and not forceManifest:
            # NFN direct result
            payload = ndn_enc.TlvEncoder()
            payload.writeBlobTlv(self.NFN_DIRECT_RESULT, data)
            c = picn_content(localName, payload.getOutput())
            pkt = picn_ndn_enc.NdnTlvEncoder()
            return pkt.encode(c) # and sign

        # NFN indirect result
        name, manifest = self.bytesToManifest(localName, data)
        payload = ndn_enc.TlvEncoder()
        payload.writeBlobTlv(self.NFN_INDIRECT_RESULT, manifest)
        c = picn_content(name, payload.getOutput())
        pkt = picn_ndn_enc.NdnTlvEncoder()
        return pkt.encode(c) # and sign

# eof

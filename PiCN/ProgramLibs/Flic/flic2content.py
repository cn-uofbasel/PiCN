#!/usr/bin/env python3

# flic2content.py
#   implements the FLIC consumer side

# (c) 2018-01-19 <christian.tschudin@unibas.ch>

class DeFLICer():

    def __init__(self, icnLayer, decoder):
        self.icnLayer = icnLayer
        self.decoder = decoder

    def _indexTable2data(self, table): # traverse the manifest tree
        # input: index table
        # output: reassembled data
        data = b''
        for ptr in table:
            p = self.decode(ptr)
            if p.T == DataPtr:
                data += self.icnLayer.readChunk(p.V)
                continue
            manifest = self.icnLayer.readChunk(p.V)
            pkt = self.decoder(manifest)
            if pkt.T != Manifest:
                raise XXX
            tbl = self.decoder(pkt.V)
            # get index table which is a list of pointers
            data += self._indexTable2data(tbl)
        return data

    def manifestToBytes(self, manifest: bytes):
        # input: chunk (containing a manifest)
        # output: re-assembled (raw e2e) bytes
        pkt = self.decoder(manifest)
        if pkt.T != Manifest:
            raise XXX
        tbl = self.decoder(pkt.V)
        # TODO: get index table which is a list of pointers
        return self._indexTable2data(tbl)

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

#!/usr/bin/env python3

# examples/write_read-flic.py
#
#  this is a demo of using the PiCN client lib for
#  first writing then reading FLICed data from the local repo (must be running)
#
# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import copy
import random
import sys
sys.path.append('..')
import time

from Layers.ChunkLayer.Chunkifyer import flic
import ProgramLibs.Client.client           as client

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    # repo must be running at localhost:9876
    icn.attach("127.0.0.1", 9876, 9876, 'ndn2013')

    data1 = bytes(random.getrandbits(8) for _ in range(16*1024 + 123))

    # store
    print("storing %d bytes via FLIC" % len(data1))
    tstamp = (time.strftime('%Y%m%d-%H%M%S') + '.txt').encode('ascii')
    name = copy.deepcopy(icn.getRepoPrefix()).__add__([tstamp, b'_'])
    name, _ = flic.MkFlic(icn).bytesToManifest(name, data1)

    # retrieve
    print("retrieving FLIC manifest '%s'" % name)
    data1copy = flic.DeFlic(icn).bytesFromManifestName(name)

    if not data1copy:
        print("ERROR: no content received")
        raise IOError

    print("retrieved content: %d bytes" % len(data1copy))
    if data1 == data1copy:
        print("  contents match!")
    else:
        print("  contents differ :-(")

    icn.detach()

# eof

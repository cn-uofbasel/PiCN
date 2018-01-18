#!/usr/bin/env python3.6

# examples/write_read.py
# (c) 2018-01-18 <christian.tschudin@unibas.ch>

import sys
sys.path.append('..')

import PiCN.client as client
import os
import time

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    icn.attach("127.0.0.1", 9876, 9876)

    pfx = icn.getRepoPrefix()
    name = pfx + '/' + time.strftime('%Y%m%d-%H%M%S') + '.txt'

    icn.writeChunk(name, "my content is known under <%s>" % name)
    c = icn.readChunk(name)
    if c:
        print("retrieved content: %s" % c)
    else:
        print("ERROR: no content received")

    icn.detach()

# eof

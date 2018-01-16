# Architecture

On one side, PiCN is a set of specialized CCN nodes and tools (data repository, forwarder, in-network compute entity; management- and fetch tools).
However, also meant to be a handy toolbox for prototyping and experimentation, PiCN includes all the building blocks to quickly assemble network nodes or tools on your own.
This document describes the building blocks of PiCN.
If your are interested in ready-to-run code, go to [Runnables](runnables.md).

### Layered Architecture

At its highest level, a node in PiCN is a stack of layers.
Each layer interacts with the next higher and lower layers only.
In general, each layer raises the level of abstraction.
Via the bottom layer, the node is connected to other nodes, while the top layer optionally interfaces with a user or application.

As an example, the stack of a vanilla relay might look as following:

|         ICN Layer         |
|:-------------------------:|
| **Packet Encoding Layer** |
| **Link Layer**            |


The Link Layer implements the face abstraction and manages the linking with neighbouring nodes. 
The Packet Encoding Layer encodes and decodes wire format packets (as used by the link layer) to python objects (as handled by the ICN layer).
The ICN Layer implements the actual logic of handling incoming interest and content object packets. Also state (CS, FIB, PIT) is maintained by the ICN layer.

By convention classes implementing a layer are placed in the packet `PiCN.Layers`.
They inherit from the class `PiCN.Processes.LayerProcess` .
On OS level each layer is a separate process.
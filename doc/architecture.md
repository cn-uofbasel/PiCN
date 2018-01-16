# Architecture

On one side, PiCN is a set of specialized CCN nodes and tools (data repository, forwarder, in-network compute entity; management- and fetch tools). However, also meant to be a handy toolbox for prototyping and experimentation, PiCN includes all the building blocks to quickly assemble network nodes or tools on your own. This document describes the building blocks of PiCN. If your are interested in ready-to-run code, go to [Runnables](runnables.md).

### Layered Architecture

At its highest level, a node in PiCN is a stack of layers. Each layer interacts with the next higher and lower layers only. Via the bottom layer, the node is connected to other nodes, while the top layer optionally interfaces with a user or application. 

The stack of a vanilla relay might look as following:

|        |
|:------:|
| xxxxxx |
| xxxxxx |
| xxxxxx |
| xxxxxx |

*This is work in progress! Everything can change at any moment! :-)*

**Requires Python  >=3.6** 

# PiCN 
PiCN is a modular ICN implementation designed to support NFN and
other in network applications written in Python 3

## Modularization
PiCN consists of several Modules which run in separated processes. 
Each Module increases the abstraction, they are chained to a kind 
of execution stack. 


## Execution Stack

### Forwarder

**Default execution Stack for a PiCN Forwarder is:**

ICNLayer 

PacketEncodingLayer

LinkLayer

Network

### Repository

**Default execution Stack for a PiCN Repository is:**

ICNRepositoryLayer

ChunkingLayer

PacketEncodingLayer

LinkLayer

Network
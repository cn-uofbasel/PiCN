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

## Management

**Commands:**

### New FACE

GET /linklayer/newface/< ip >:< targetport > HTTP/1.1\r\n\r\n

### New Forwarding Rule

GET /icnlayer/newforwardingrule/< name >:< faceid > HTTP/1.1\r\n\r\n

Use "%2F" to separate components in the name (URL Encoding for "/")

### New Content 

GET /icnlayer/newcontent/< name >:< data > HTTP/1.1\r\n\r\n

Use "%2F" to separate components in the name (URL Encoding for "/")

### Shutdown, Terminate Process

GET /shutdown HTTP/1.1\r\n\r\n

## Executables

### Forwarder
python PiCn/Executable/ICNForwarder.py < listeningport >

### Repository
python PiCn/Executable/ICNDataRepository.py < path on disk > < ICN prefix > < listeningport >


### Simple Fetch
python PiCn/Executable/Fetch.py < ip > < port > < name >

### Fetch (with chunk support)
python PiCn/Executable/Fetch.py < ip > < port > < name >

### Mgmt
python PiCn/Executable/Mgmt.py < ip > < port > < command > [ < param > ]

command: (newface < ip >:< targetport > | newforwardingrule < name >:< faceid > | newcontent < name >:< data > | shutdown)

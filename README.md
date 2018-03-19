*This is work in progress! Everything can change at any moment! :-)*

# PiCN 

[![Build Status](https://semaphoreci.com/api/v1/cn-unibas/picn/branches/master/badge.svg)](https://semaphoreci.com/cn-unibas/picn)

PiCN is a...
* prototyping-friendly, modular and extensible library for content-centric networkig (CCN).
* a set of tools and network nodes.
* our platform to build the next generation of NFN.

PiCN is written in Python 3.6+


## Quick start
This is a simple example that shows how to start a Repository and a Forwarder and how to fetch Content from the Repo.
The following topology is used:

**Client(Fetch Tool) ---- Forwarder ---- Repo**
             
Clone PiCN from github:
```console
you@machine:~$ git clone https://github.com/cn-uofbasel/PiCN.git
```

Add the PiCN-tools to your PATH (bash):
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/starter
```

Prepare content for a repository:
```console
you@machine:~$ mkdir /tmp/repo
you@machine:~$ touch /tmp/repo/example && echo "HELLO WORLD" > /tmp/repo/example
...
```

Start a repository node and a forwarder:
```console
you@machine:~$ picn-repo --format ndntlv /tmp/repo /the/prefix 10000 &
you@machine:~$ picn-relay --format ndntlv --port 9000 &  
...
```

Configure a forwarding rule from the forwarder to the repository:
```console
you@machine:~$ picn-mgmt --ip 127.0.0.1 --port 9000 newface 127.0.0.1:10000
you@machine:~$ picn-mgmt --ip 127.0.0.1 --port 9000 newforwardingrule /the:0
...
```

Fetch content from the repository via the forwarding node:
```console
you@notebook:~$ picn-fetch --format ndntlv 127.0.0.1 9000 /the/prefix/example 
... todo ...
```

## Named Function Networking
%TODO

## Chunking
PiCN ships with a build in Chunking Tool. If the data do not fit a packet, the ChunkLayer will autmatically split the
content into Chunks (NDN Terminology: Segments). 
We use a on-demand chunking process

If a data object has to be chunked, the Repo will return a Metadata-Object.
 
A Metadata-Object contains the names of up to 4 chunks and a pointer to the next Metadata-Object.
The following name scheme is used:

* Metadata-Object naming:
  * First Metadata-Object: < original file name > 
  * Second Metadata-Object: < original file name  >/m1
  * n-th Metadata-Object: < original file name>/mn
  
* Metadata object content: 

  mdo: < name first chunk name> : < name second chunk name> : < name third chunk name> : < name fourth chunk name>  : < next meta data object >
  
  * The content is complete if there is no further Metadata-Object.
  
* Chunk Naming: 
  * First Chunk < original file name >/c0
  * Second Chunk < original file name >/c1
  * n-th Chunk < original file name >/cn

The Fetch-Tool will automatically reassable the chunks and return the complete content object. 


Warning: Currently, the chunking is done using the main memory. Therefore the maximal file size is limited.
This will be improved soon.

## Layers
%TODO

### ICN Layer
%TODO

#### Forwarder app, to app forwarding
%TODO

## Developer guide

### Modularization
PiCN consists of several Modules which run in separated processes. 
Each Module increases the abstraction, they are chained to a kind 
of execution stack.

### ProgramLibs
%TODO


## Compatible with:
[![Named Data Networking (NDN)](https://named-data.net/wp-content/uploads/cropped-20130722_Logo2.png)](https://named-data.net)




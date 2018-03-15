*This is work in progress! Everything can change at any moment! :-)*

**Requires Python  >=3.6** 

# Status of Automatic Tests

[![Build Status](https://semaphoreci.com/api/v1/cn-unibas/picn/branches/master/badge.svg)](https://semaphoreci.com/cn-unibas/picn)

(The CI system runs unit tests, that verify the functionality of PiCN, including network communication)

# PiCN 
PiCN is a modular implementation of Information Centric Networking (ICN) designed to support Named Function Networking (NFN)
and other in network applications written in Python 3.

Currently, PiCN is compatible with the [Named Data Networking (NDN) packet format](https://named-data.net).


# Quick start
```
#Download PiCN
% git clone https://github.com/cn-uofbasel/PiCN.git
% cd PiCN
% export PYTHONPATH=`pwd`
...
#Setup folder for the repo
% mkdir /tmp/repo
% touch /tmp/repo/example && echo "HELLO WORLD" > /tmp/repo/example
...
#Start Repo and Forwarder
% python3 ./PiCN/Executable/ICNDataRepository.py --format ndntlv /tmp/repo /the/prefix 10000 &
% python3 ./PiCN/Executable/ICNForwarder.py --format ndntlv --port 9000 & 
% 
...
#Setup forwarding rule
% python3 ./PiCN/Executable/Mgmt.py -i 127.0.0.1 -p 9000 newface 127.0.0.1 10000
% python3 ./PiCN/Executable/Mgmt.py -i 127.0.0.1 -p 9000 newforwardingrule /the 0
...
#Fetch content from the Repo 
% python3 ./PiCN/Executable/Fetch.py --format ndntlv 127.0.0.1 9000 /the/prefix/example 
```

# Named Function Networking
%TODO

# Developer guide

## Modularization
PiCN consists of several Modules which run in separated processes. 
Each Module increases the abstraction, they are chained to a kind 
of execution stack.

### Layers
%TODO

### ProgramLibs
%TODO


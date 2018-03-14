*This is work in progress! Everything can change at any moment! :-)*

**Requires Python  >=3.6** 

# Status of Automatic Tests

[![Build Status](https://semaphoreci.com/api/v1/cn-unibas/picn/branches/master/badge.svg)](https://semaphoreci.com/cn-unibas/picn)

(The CI system runs unit tests, that verify the functionality of PiCN, including network communication)

# PiCN 
PiCN is a modular ICN implementation designed to support NFN and
other in network applications written in Python 3

## Modularization
PiCN consists of several Modules which run in separated processes. 
Each Module increases the abstraction, they are chained to a kind 
of execution stack.

# Quick start
```
% git clone https://github.com/cn-uofbasel/PiCN.git
% cd PiCN
% export PYTHONPATH=`pwd`
...
% mkdir /tmp/repo
% touch /tmp/repo/example && echo "HELLO WORLD" > /tmp/repo/example
...
% python3 ./PiCN/Executable/ICNDataRepository.py --format ndntlv /tmp/repo /the/prefix 10000 &
% python3 ./PiCN/Executable/ICNForwarder.py --format ndntlv --port 9000 & 
% 
...
...
...
```
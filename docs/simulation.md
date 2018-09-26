# PiCN Simulation System

PiCN includes a simple Simulation System, which helps to verify the forwarding process and can 
be used for tests. 

In fact, for its simulation system, PiCN starts multiple forwarders on a single machine and uses 
a simulation interface to communicate with each other. 
Therefore, the simulation is quiet similar to running an actual network. 

## Getting Started with the Simulations

In this Getting Started tutorial we will take the example from the [NFN Tutorial](nfn.md) and
transform it into a PiCN Simulation.

### Setup

To use the PiCN Simulation System one has to clone PiCN

```console
you@machine:~$ https://github.com/cn-uofbasel/PiCN.git
```
and add the root directory of PiCN to the Python-path of the system. 
```console
you@machine:~$ cd PiCN && export PYTHONPATH=${PYTHONPATH}:`pwd`
```

### Creating a new Simulation with two nodes.
Once, you finished the setup, you can create a new Python file, which will contain your simulation. 
```console
you@machine:~$ touch example_simulation.py 
```

Open the file and add the imports for the simulation. In our simulation we use the NFNForwarder
for forwarding and computing results. Furthermore we will use the fetch tool the receive the result.

```python
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
```
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

Open the file **example_simulation.py** and add the imports for the simulation. In our simulation we use the NFNForwarder
for forwarding and computing results. Furthermore we will use the fetch tool the receive the result.

```python
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
```

To run a simulation it is required to have the simulation system available
```python
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
``` 

To setup a NFN forwarder, we need an encoder, so we need to import: 
```python 
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
``` 

To manage the forwarders and to install forwarder, the Mgmt tool is required. 
```python
from PiCN.Mgmt import MgmtClient
```

Last, we need functionallity for creating names etc. 
```python
from PiCN.Packets import Content, Interest, Name
```

**After adding the imports to the file, we now can start setting up our network.**

First we need a simulation_bus, which is used to connect the relays to each other.
```python
simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder)
```

For this simple simulation we need two NFN forwarders:
```python
nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                         interfaces=[simulation_bus.add_interface("nfn0")], log_level=255,
                         ageing_interval=1)
```
This command creates a new forwarder. The system will decide which port is used for managment (port=0).
The encode is the NDNTLV encoder. As interface we create a new interface with the name **nfn0**.
The logger is disabled, and the ageing interval is 1 sec.

Next, create the second forwarder.
```python
nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                         interfaces=[simulation_bus.add_interface("nfn1")], log_level=255,
                         ageing_interval=1)
```

For both forwarders we need a Mgmt Client:
```python
mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])
```

To issue an interest, we need an instance of the Fetch tool.
```python
fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtool1")])
```
The Fetch tool is connected with the **nfn_fwd0** forwarder.

Now we have all required tools available, and we can start them:
```python
nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
simulation_bus.start_process()
```

Next, we install a face from nfn_fwd0 to nfn_fwd1:
```python
mgmt_client0.add_face("nfn1", None, 0)
```

And next we install a forwarding rule from nfn_fwd0 to nfn_fwd1 with the prefix **/data**
```python
mgmt_client0.add_forwarding_rule(Name("/data"), [0])
```

We put a named function in the cache of nfn_fwd0: 

```python
mgmt_client0.add_new_content(Name("/func/combine"), "PYTHON\nfunc\ndef func(a, b):\n    return a + b")
```

and we put a content object in the cache of nfn_fwd1: 
```python
mgmt_client1.add_new_content(Name("/data/obj1"), "World")
```

To request a result we create a workflow and encode it into a name.
```python

name = Name("/func/combine")
name += '_("Hello",/data/obj1)'
name += "NFN"
```

Now the setup is completed and we can run the simulation by issuing an interest message.
```python
res = fetch_tool.fetch_data(name, timeout=20)
print(res)
```
You will see the system printing the packet that are sent between the nodes.


At the end we shutdown all running instances: 
```python
nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
```

### The entire code of the simulation
You can find the Tutorial Code [here](../PiCN/Simulations/SimulationsTutorial.py).

```python
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Content, Interest, Name

simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder)
nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                         interfaces=[simulation_bus.add_interface("nfn0")], log_level=255,
                         ageing_interval=1)
                         
nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                         interfaces=[simulation_bus.add_interface("nfn1")], log_level=255,
                         ageing_interval=1)
                         
mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtool1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
mgmt_client0.add_forwarding_rule(Name("/data"), [0])

mgmt_client0.add_new_content(Name("/func/combine"), "PYTHON\nfunc\ndef func(a, b):\n    return a + b")
mgmt_client1.add_new_content(Name("/data/obj1"), "World")

name = Name("/func/combine")
name += '_("Hello",/data/obj1)'
name += "NFN"

res = fetch_tool.fetch_data(name, timeout=20)
print(res)

nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()

```
### Other Tools

By importing the ProgramLibs for the Repo or the ICNForwarder you can use those tools in a simulation, too:

```python
import PiCN.ProgramLibs.ICNDataRepository
import PiCN.ProgramLibs.ICNForwarder
```


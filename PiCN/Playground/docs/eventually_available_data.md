# Delivery of Eventually-Available Data

This how-to..


## Sample Topology

![Sample Topology](https://raw.githubusercontent.com/cn-uofbasel/PiCN/nof18-doc/PiCN/Playground/docs/img/setup.png "Sample Topology")

For both approaches, our sample topology simply consists of a packet forwarder which hands over computation result requests to a computation node.

* Nodes are connected via UDP faces: The packet forwarder listens on port 9000 and the computation server on on port 8000.
* A forwarding rule is configured on the packet fowarder to forward interests prefixed with `/the/prefix` to the computation node.
* The computation node comes with a function store where services are saved. When starting a computation node, the services `/xxx/xxx/xxx` and `/xxx/xxx/xxx` are automatically added.
* The reader of this how-to will request eventually-available computation results via the forwarder from the computation server. for this purpose, client tools are available which implement the consumption logic. In real-world applications, this logic would be implemented by the client application.


## Preparation

Requirements: Make sure, that git and python3.6+ is available on your system. PiCN is tested on Linux and Mac OS X. Windows is also supported but not extensively tested.

If not already available on your machine, clone PiCN from Github:
```console
you@machine:~$ git clone https://github.com/cn-uofbasel/PiCN.git
```

To start nodes and manage these from the command line, PiCN comes with scripts.

Add the core PiCN tools to your PATH (bash):
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/starter
```

Also add tools for eventually-available data retrieval tools to your PATH (bash):
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/Playground/starter
```
We recommend to add these lines to ~/.bashrc (bash).

If the tools are available, you see usage information after typing the following commands:

```console
you@machine:~$ picn-forwarder --help
```

```console
you@machine:~$ picn-heartbeat-forwarder --help
```


## Heartbeat Approach

### Starting Nodes

Open a terminal and type the following commmand to start a packet forwarding node:

```console
you@machine:~$ picn-heartbeat-forwarder ............
```

...tod... explanation

Type in another terminal the following command to start the computation server:

```console
you@machine:~$ picn-heartbeat-server ............
```

... todo.. explanation

You should see something similar that the following.

...todo screenshot...

### Forwarding Rule

...

### Request Content

...

## Two-Phase Request Approach

..

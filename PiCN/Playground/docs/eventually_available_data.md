# Delivery of Eventually-Available Data

This how-to..

## Sample Topology

![Sample Topology](https://raw.githubusercontent.com/cn-uofbasel/PiCN/nof18-doc/PiCN/Playground/docs/img/setup.png "Sample Topology")

For both approaches, our sample topology simply consists of a packet forwarder which hands over computation result requests to a computation node. Nodes are connected via UDP faces: The packet forwarder listens on port 9000 and the computation server on on port 8000. A forwarding rule is configured on the packet fowarder to forward interests prefixed with `/the/prefix` to the computation node. The computation node comes with a function store where services are saved. When starting a computation node, the services `/xxx/xxx/xxx` and `/xxx/xxx/xxx` are automatically added. The reader of this how-to will request eventually-available computation results via the forwarder from the computation server. for this purpose, client tools are available which implement the consumption logic. In real-world applications, this logic would be implemented by the client application.

## Preparation

If not already available on your machine, clone PiCN from github:
```console
you@machine:~$ git clone https://github.com/cn-uofbasel/PiCN.git
```

PiCN comes with...

Add the PiCN-tools to your PATH (bash):
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/starter
```

Also add ....:
```console
you@machine:~$ PATH=$PATH:`pwd`/PiCN/Playground/starter
```

We recomment to add this lines to ,,, (e.g. `~/.bashrc` for bash).

## Heartbeat Approach

..

## Two-Phase Request Approach

..

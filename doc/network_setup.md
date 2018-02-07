# Setting up a Network

The tool `picn-setup` automatically sets up a network of PiCN nodes within a `tmux` session.
Each node is started with separate window such that output is easy to access.
You can select from a set of predefined network configurations.

```
Usage: picn-setup CONFIG
CONFIG:
  fwd_to_testbed  --   Two hops to the NDN testbed
```

## How to Install `picn-setup`?

`picn-setup` is part of the [PiCN tools](runnables.md).

## Network Configurations

### fwd_to_testbed

> `picn-setup fwd_to_testbed`

* PiCN forwarder listening on 9000
* PiCN forwarder listening on 9001

* Content object `/ndn/ch/unibas/test` in CS of forwarder with port 9001

* Forwarding rule from `9000` to `9001` for prefix `/ndn/ch/unibas`
* Forwarding rule from `9001` to NDN testbed for prefix `/ndn/ch/unibas`

### more..

More configurations will follow...


## Changing the Default Behaviour

With environment variables the default behavior of `picn-setup` can be changed:

* `INITPORT`: UDP port for nodes start from here (default: `9000`)
* `NDNTESTBED`: Entry point to the NDN testbed (default: `dmi-ndn-testbed1.dmi.unibas.ch`) 
* `LOGLEVEL`: Log level (default: `info`)
* `SESSION`: Name of tmux session (default: `picn-setup`)
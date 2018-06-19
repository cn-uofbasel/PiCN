# Setting up a Network

The `picn-setup` tool automatically sets up a bunch of PiCN nodes, creates faces, installs forwarding rules and adds content.
To keep track on what is going on, a setup runs in a `tmux` session where each node is executed within a separate `window.

```
Usage: picn-setup CONFIG
CONFIG:
  fwd_to_testbed  --   Two hops to the NDN testbed
```


## What is tmux?!?

The manual page says:

```
tmux is a terminal multiplexer: it enables a number of terminals to be created, accessed,
and controlled from a single screen.  tmux may be detached from a screen and continue
running in the background, then later reattached. A session is a single collection of
pseudo terminals under the management of tmux.  Each session has one or more windows
linked to it.
```

**Survival Kit:**
 
 * Switch to next window in a tmux session (keyboard shortcut): `Ctrl` + `n`
 * Detach session (keyboard shortcut): `Ctrl` + `d`
 * Attach the session (shell command): `tmux attach -t picn-setup`
 * Kill the detached session (shell command): `tmux kill-session -t picn-setup`


## How to Install `picn-setup`?

`picn-setup` is contained by the [PiCN toolbox](toolbox.md).


## Network Configurations

### fwd_to_testbed

> `picn-setup fwd_to_testbed`

* Packet format: `ndntlv`

* PiCN forwarder listening on UDP port 9000
* PiCN forwarder listening on UDP port 9001

* Content object `/ndn/ch/unibas/test` in content store of forwarder with port 9001

* Forwarding rule from `9000` to `9001` for prefix `/ndn/ch/unibas`
* Forwarding rule from `9001` to [NDN testbed](https://named-data.net/ndn-testbed) for prefix `/ndn/ch/unibas`


![Configuration fwd_to_testbed](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/docs/img/configuration_fwd_to_testbed.png "Configuration fwd_to_testbed")


### More Configurations..

More configurations will follow...


## Changing the Default Behaviour

With environment variables the default behavior of `picn-setup` can be changed:

* `INITPORT`: UDP port for nodes start from here (default: `9000`)
* `NDNTESTBED`: Entry point to the [NDN testbed](https://named-data.net/ndn-testbed) (default: `dmi-ndn-testbed1.dmi.unibas.ch`) 
* `LOGLEVEL`: Log level (options: `debug`, `info`, `warning`, `error`, `none` / default: `info`)
* `SESSION`: Name of tmux session (default: `picn-setup`)

---

**Enhancements:** See [issue #10](https://github.com/cn-uofbasel/PiCN/issues/10).

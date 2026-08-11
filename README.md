# PiCN

[![CI](https://github.com/cn-uofbasel/PiCN/actions/workflows/ci.yml/badge.svg)](https://github.com/cn-uofbasel/PiCN/actions/workflows/ci.yml)

PiCN is a:

* prototyping-friendly, modular library for Information-Centric Networking (ICN / CCN)
* set of tools and network nodes (forwarder, repository, fetch, management)
* platform for [Named Function Networking (NFN)](docs/nfn.md)
* simple [simulation system](docs/simulation.md) for ICN and NFN

PiCN supports **Python 3.14** and includes an **asyncio** runtime alongside the
original multiprocessing-per-layer path (`--runtime sync|async`, default
**sync**, so existing workflows keep working unchanged). See
[`docs/modernization.md`](docs/modernization.md) for how the migration got
here and [`docs/design-adrs/`](docs/design-adrs/README.md) for the design
rationale behind the dual runtime.

| Topic | Doc |
|---|---|
| Architecture (layers + dual runtime) | [`docs/architecture.md`](docs/architecture.md) |
| Package layout | [`docs/project_structure.md`](docs/project_structure.md) |
| Design decisions (ADRs) | [`docs/design-adrs/`](docs/design-adrs/README.md) |
| Contributor conventions | [`AGENTS.md`](AGENTS.md) |

## Features

#### Library

* Link Layer (UDP faces, simulation bus)
* Packet Encoding Layer (NDN TLV + simple string format)
* ICN Layer (forwarding, CS / FIB / PIT)
* Chunking, repository, NFN / thunk / routing / autoconfig layers
* Management interface (sync process or async TCP task)

#### Tools (`starter/`)

* `picn-relay` — ICN forwarder (`--runtime sync|async`)
* `picn-nfn` — NFN forwarder (`--runtime sync|async`)
* `picn-repo` / `picn-pushrepo` — content repositories
* `picn-fetch` / `picn-peek` — fetch tools (`picn-fetch` supports `--runtime`)
* `picn-mgmt` — management client
* `picn-setup` — multi-node setup helper

## Requirements

* **Python ≥ 3.14** (see `pyproject.toml`)
* No hard runtime dependencies for the default CLI path
* Optional: `pip install "PiCN[dev]"` for pytest; `pip install "PiCN[config]"` for `picn-relay -c` TOML configs (`pytoml`)

## Setup

```console
git clone https://github.com/cn-uofbasel/PiCN.git
cd PiCN
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export PATH="$PATH:$(pwd)/starter"
# starter scripts also set PYTHONPATH to the repo root
```

Alternatively without editable install: `export PYTHONPATH=$(pwd)` and put `starter/` on your `PATH`.

## Getting Started (ICN)

Set up a repository and a forwarding node:

![Hands On: Topology](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/docs/img/initial-hands-on.png "Hands On: Topology")

Prepare content:

```console
mkdir -p /tmp/repo
echo "HELLO WORLD" > /tmp/repo/example
```

Start a repository and a forwarder (default **sync** runtime):

```console
picn-repo --format ndntlv /tmp/repo /the/prefix 10000 &
picn-relay --format ndntlv --port 9000 &
```

Configure a face and forwarding rule:

```console
picn-mgmt --ip 127.0.0.1 --port 9000 newface 127.0.0.1:10000:0
picn-mgmt --ip 127.0.0.1 --port 9000 newforwardingrule /the:0
```

You can also install a rule that fans out to multiple faces (e.g. face-ids 0 and 1):

```console
picn-mgmt --ip 127.0.0.1 --port 9000 newforwardingrule /prefix:0,1
```

Fetch content via the forwarder:

```console
picn-fetch --format ndntlv 127.0.0.1 9000 /the/prefix/example
HELLO WORLD
```

### Async runtime (optional)

Relay and fetch accept `--runtime async` (one event loop per node instead of
one process per layer). Example:

```console
picn-relay --format ndntlv --port 9000 --runtime async &
picn-fetch --format ndntlv --runtime async 127.0.0.1 9000 /the/prefix/example
```

Details: [`docs/architecture.md`](docs/architecture.md).

## Getting Started with NFN

NFN is a computation engine for ICN: express how data should be transformed;
the network finds where to compute. Tutorial: [`docs/nfn.md`](docs/nfn.md).

Minimal sketch (commands unchanged; add `--runtime async` on `picn-nfn` /
`picn-fetch` if desired):

```console
picn-nfn --port 9000 --format ndntlv -l debug &
picn-nfn --port 9001 --format ndntlv -l debug &
picn-mgmt --port 9000 newface 127.0.0.1:9001:0
picn-mgmt --port 9000 newforwardingrule /data:0
# … install function + data via picn-mgmt newcontent, then:
picn-fetch 127.0.0.1 9000 '/func/combine("Hello",/data/obj1)/NFN'
```

## Tests and CI

```console
python -m pytest PiCN/ --ignore=PiCN/Simulations -q --timeout=90
```

GitHub Actions (this branch): **fast** suite on every push; **full** suite
(Ubuntu + macOS) on pull requests and `workflow_dispatch`. Simulations are
excluded from CI (slow / environment-sensitive).

## More about…

### Operational

* [PiCN Toolbox](docs/toolbox.md)
* [Setting up a Network](docs/network_setup.md)
* [PiCN runnables as systemd service](https://github.com/cn-uofbasel/PiCN-systemd-service)
* [Packet Formats](docs/packet_formats.md)
* [Simulation System](docs/simulation.md)

### Internals

* [Architecture](docs/architecture.md)
* [Project Structure](docs/project_structure.md)
* [Management Interface](docs/management_interface.md)
* [Design decisions (ADRs)](docs/design-adrs/README.md)

### Migration history

The asyncio/Python 3.14 migration is complete. Its rationale and verification
record are kept for reference: [plan and current-state audit](docs/modernization.md) ·
[per-phase test evidence](docs/baseline.md).

### The project

* [Licensing](docs/licensing.md)
* Upstream mailing list: [picn@unibas](https://www.maillist.unibas.ch/mailman/listinfo/picn)

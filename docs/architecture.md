# Architecture

On one side, PiCN is a set of specialized CCN nodes and tools (data repository, forwarder, in-network compute entity; management- and fetch tools).
However, also meant to be a handy toolbox for prototyping and experimentation, PiCN includes all the building blocks to quickly assemble network nodes or tools on your own.
This document describes the building blocks of PiCN.
If you are interested in ready-to-run code, go to [Runnables](toolbox.md).

Since the Python 3.14 / asyncio migration, PiCN keeps this layered model and
adds a parallel **asyncio** execution path. Protocol behaviour (packet formats,
forwarding semantics) is unchanged; see [modernization.md](modernization.md).

### Layered Architecture

At its highest level, a node in PiCN is a stack of layers.
Each layer interacts with the next higher and lower layers only.
In general, each layer raises the level of abstraction.
Via the bottom layer, the node is connected to other nodes, while the top layer optionally interfaces with a user or application.

As an example, the stack of a vanilla relay might look as following:

|         ICN Layer         |
|:-------------------------:|
| **Packet Encoding Layer** |
| **Link Layer**            |


The Link Layer implements the face abstraction and manages the linking with neighbouring nodes.
The Packet Encoding Layer encodes and decodes wire format packets (as used by the link layer) to python objects (as handled by the ICN layer).
The ICN Layer implements the actual logic of handling incoming interest and content object packets. Also state (CS, FIB, PIT) is maintained by the ICN layer.

By convention classes implementing a layer are placed in the package `PiCN.Layers`.

### Dual runtime (sync and async)

ProgramLibs (`ICNForwarder`, `NFNForwarder`, `Fetch`, repositories, …) accept
`runtime="sync"|"async"` (default **`sync`**):

| | **sync** (default) | **async** |
|---|---|---|
| Layer base | `PiCN.Processes.LayerProcess` | `PiCN.Processes.AsyncLayerProcess` |
| Stack | `LayerStack` + `multiprocessing.Queue` | `AsyncLayerStack` + `asyncio.Queue` |
| Execution | one OS process per layer | one `asyncio.Task` per layer, one event loop per node |
| Tables | `PiCNSyncDataStructFactory` / Manager | plain in-process CS/FIB/PIT/FaceIDTable |
| Link I/O | `BasicLinkLayer` + `select`/`poll` on `file_descriptor` | `AsyncBasicLinkLayer` + `register()` / `send_async()` |
| Management | `Mgmt` (TCP server in its own process) | `AsyncMgmt` (TCP server task in the node loop) |
| Start / stop | `start_forwarder()` / `stop_forwarder()` | `await start_forwarder_async()` / `await stop_forwarder_async()` |

Shared packet-handling logic lives in non-process `*Core` modules
(returning `List[Outbound]`); sync and async wrappers both call into those
cores. See `docs/modernization.md` and `docs/design-adrs/`.

**Simulations:** `SimulationBus` remains a multiprocessing dispatcher. Async
nodes attach via `SimulationInterface.register()` (Phase 5.7 pattern).

Full removal of the sync/multiprocessing path is deferred until a later
phase that retires `runtime=sync`.

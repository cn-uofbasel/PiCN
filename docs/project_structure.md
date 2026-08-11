# Package Structure

Package layout of PiCN, including the dual sync/async runtime added by the
Python 3.14 / asyncio migration (see [modernization.md](modernization.md)).

### Top level

* **`starter/`**: shell wrappers (`picn-relay`, `picn-nfn`, `picn-repo`, `picn-fetch`, `picn-mgmt`, …) that set `PYTHONPATH` and invoke `PiCN/Executable/`
* **`docs/`**: architecture, modernization plan, ADRs, baseline
* **`PiCN/`**: library and program packages (below)

### `PiCN/`

* **`Executable`**: CLI entry points wrapping ProgramLibs
  * `--runtime sync|async` on relay / NFN / fetch (default sync)
  * `Helpers/async_runtime.py`: SIGINT-aware `run_until_signal` for async mains
  * Optional TOML config for the relay: `pip install "PiCN[config]"` (`pytoml`), used only with `-c/--config`
* **`Layers`**: *One package per layer; each migrated layer has*
  * `Basic*Layer` — sync `LayerProcess` wrapper (default ProgramLib path)
  * `*Core` — process-free handlers returning `Outbound` lists
  * `AsyncBasic*Layer` — `AsyncLayerProcess` wrapper for `runtime=async`
  * `LinkLayer`: also `AsyncBasicLinkLayer`, `RunStrategy` (Sync/Async), interfaces (`UDP4`, `Simulation`)
* **`Logger`**: *Logging helpers*
* **`Mgmt`**: *`Mgmt` (sync process) and `AsyncMgmt` (asyncio TCP)*
* **`Packets`**: *Wire format helpers*
* **`Processes`**: *`LayerProcess` / `PiCNProcess` (sync); `AsyncLayerProcess`; `Outbound`; Manager factory for sync tables*
* **`LayerStack`**: *`LayerStack` (MP queues) and `AsyncLayerStack` (asyncio queues + stack executor)*
* **`ProgramLibs`**: *Node assemblies*
  * `runtime.py` — `Runtime` enum + `make_forwarding_tables`
  * `ICNForwarder`, `NFNForwarder`, `Fetch`, `ICNDataRepository`, `ICNPushRepository`
* **`Simulations`**: *Multi-node scenarios (`SimulationBus` still MP); includes `SimulationsTutorial_async.py`*
* **`Routing`**: *TBD*

Experimental `Playground/` demos were removed in Phase 6 (MP `LayerProcess`
prototypes). Data-offloading chunk layers / `NFNForwarderData` were also
removed; use `NFNForwarder` instead.

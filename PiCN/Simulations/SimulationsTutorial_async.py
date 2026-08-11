"""SimulationsTutorial under async ProgramLibs (Phase 5.7).

One shared event loop for every async node -- do not call asyncio.run() per
forwarder. SimulationBus remains a sync Process (Phase 3 SimulationInterface).
"""

import asyncio

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.runtime import Runtime
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name


def _unblock_sim_interfaces(*nodes) -> None:
    """Wake SimulationInterface register() pumps blocked on queue_from_bus.get()."""
    for node in nodes:
        for iface in getattr(node, "interfaces", []) or []:
            q = getattr(iface, "queue_from_bus", None)
            if q is not None:
                try:
                    q.put(["teardown", b""])
                except Exception:
                    pass
            try:
                iface.close()
            except Exception:
                pass


async def run_tutorial_async() -> str:
    """Run the tutorial NFN exchange under Runtime.ASYNC. Returns the result."""
    encoder = NdnTlvEncoder()
    simulation_bus = SimulationBus(packetencoder=encoder)

    nfn_fwd0 = NFNForwarder(
        port=0, encoder=encoder,
        interfaces=[simulation_bus.add_interface("nfn0")],
        log_level=255, ageing_interval=1, runtime=Runtime.ASYNC)
    nfn_fwd1 = NFNForwarder(
        port=0, encoder=encoder,
        interfaces=[simulation_bus.add_interface("nfn1")],
        log_level=255, ageing_interval=1, runtime=Runtime.ASYNC)
    fetch_tool = Fetch(
        "nfn0", None, 255, encoder,
        interfaces=[simulation_bus.add_interface("fetchtool1")],
        runtime=Runtime.ASYNC)

    await nfn_fwd0.start_forwarder_async()
    await nfn_fwd1.start_forwarder_async()
    await fetch_tool.start_fetch_async()
    simulation_bus.start_process()

    loop = asyncio.get_running_loop()
    try:
        mgmt0 = MgmtClient(nfn_fwd0.mgmt.port)
        mgmt1 = MgmtClient(nfn_fwd1.mgmt.port)
        # Sync MgmtClient uses blocking sockets -- run off the event loop.
        await loop.run_in_executor(None, mgmt0.add_face, "nfn1", None, 0)
        await loop.run_in_executor(
            None, mgmt0.add_forwarding_rule, Name("/data"), [0])
        await loop.run_in_executor(
            None, mgmt0.add_new_content, Name("/func/combine"),
            "PYTHON\nfunc\ndef func(a, b):\n    return a + b")
        await loop.run_in_executor(
            None, mgmt1.add_new_content, Name("/data/obj1"), "World")

        name = Name("/func/combine")
        name += '_("Hello",/data/obj1)'
        name += "NFN"
        return await fetch_tool.fetch_data_async(name, timeout=20)
    finally:
        # Close simulation queues first so register() pumps unblock their
        # executor workers before AsyncLayerStack.executor.shutdown(wait=True).
        _unblock_sim_interfaces(nfn_fwd0, nfn_fwd1, fetch_tool)
        await fetch_tool.stop_fetch_async()
        await nfn_fwd0.stop_forwarder_async()
        await nfn_fwd1.stop_forwarder_async()
        simulation_bus.stop_process()


def main():
    res = asyncio.run(run_tutorial_async())
    print(res)


if __name__ == "__main__":
    main()

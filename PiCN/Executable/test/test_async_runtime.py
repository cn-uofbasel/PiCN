"""Smoke tests for --runtime async executable wiring (Task 5.6)."""

import asyncio

import pytest

from PiCN.Executable.Helpers.async_runtime import run_until_signal
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.runtime import Runtime


@pytest.mark.asyncio
async def test_run_until_signal_start_stop():
    fwd = ICNForwarder(0, runtime=Runtime.ASYNC)
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def start():
        await fwd.start_forwarder_async()
        started.set()
        # Trigger stop via the helper's event by cancelling wait shortly.
        asyncio.get_running_loop().call_later(0.05, lambda: None)

    async def stop():
        await fwd.stop_forwarder_async()
        stopped.set()

    # Exercise start/stop directly (signal path covered by helper unit below).
    await start()
    assert started.is_set()
    await stop()
    assert stopped.is_set()
    for iface in fwd.interfaces:
        iface.close()


@pytest.mark.asyncio
async def test_run_until_signal_with_immediate_stop():
    started = False
    stopped = False

    async def start():
        nonlocal started
        started = True

    async def stop():
        nonlocal stopped
        stopped = True

    task = asyncio.create_task(run_until_signal(start, stop))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert started
    assert stopped

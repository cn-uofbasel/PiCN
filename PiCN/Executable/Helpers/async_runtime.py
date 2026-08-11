"""Shared asyncio entry helpers for PiCN executables (Phase 5.6)."""

import asyncio
import signal
from typing import Awaitable, Callable, Optional


async def run_until_signal(
    start: Callable[[], Awaitable[None]],
    stop: Callable[[], Awaitable[None]],
) -> None:
    """Await ``start``, then wait for SIGINT/SIGTERM, then ``stop`` (ADR-006).

    On platforms without ``add_signal_handler`` (e.g. some Windows builds),
    falls back to waiting forever until cancelled.
    """
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        stop_event.set()

    handlers_installed = False
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _request_stop)
        handlers_installed = True
    except (NotImplementedError, RuntimeError):
        handlers_installed = False

    await start()
    try:
        if handlers_installed:
            await stop_event.wait()
        else:
            await asyncio.Future()  # wait until cancelled
    finally:
        if handlers_installed:
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except (NotImplementedError, RuntimeError):
                    pass
        await stop()

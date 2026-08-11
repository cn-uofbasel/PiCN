"""Async NFNForwarder smoke tests (Task 5.4)."""

import pytest

from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.runtime import Runtime


class TestNFNForwarderAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        fwd = NFNForwarder(0, log_level=255, runtime=Runtime.ASYNC)
        await fwd.start_forwarder_async()
        try:
            assert fwd.lstack.executor is not None
            assert fwd.mgmt._server is not None
        finally:
            await fwd.stop_forwarder_async()
            for iface in fwd.interfaces:
                iface.close()

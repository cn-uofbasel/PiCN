"""Async ICNDataRepository smoke test (Task 5.5)."""

import pytest

from PiCN.Packets import Name
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.runtime import Runtime


class TestICNDataRepositoryAsync:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        repo = ICNDataRepository(None, Name("/test/repo"), port=0, runtime=Runtime.ASYNC)
        await repo.start_repo_async()
        try:
            assert repo.lstack.executor is not None
        finally:
            await repo.stop_repo_async()
            for iface in repo.interfaces:
                iface.close()

"""Phase 5.7 — SimulationsTutorial under async ProgramLibs."""

import pytest

from PiCN.Simulations.SimulationsTutorial_async import run_tutorial_async


@pytest.mark.asyncio
async def test_simulations_tutorial_async_nfn_exchange():
    result = await run_tutorial_async()
    assert result is not None
    assert "Hello" in str(result) or "World" in str(result) or result == "HelloWorld"

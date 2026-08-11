"""Pure helpers for NFN executor calls (ADR-009).

Safe to pass to ``loop.run_in_executor`` — no layer ``self``.
"""

from typing import List, Optional

from PiCN.Layers.NFNLayer.NFNExecutor import BaseNFNExecutor


def run_nfn_executor_execute(
    nfn_executor: BaseNFNExecutor,
    function_code: str,
    params: List,
    packetid: int,
    comp_name: str,
) -> Optional[str]:
    """Run ``BaseNFNExecutor.execute`` in a worker thread."""
    return nfn_executor.execute(
        function_code=function_code,
        params=params,
        packetid=packetid,
        comp_name=comp_name,
    )

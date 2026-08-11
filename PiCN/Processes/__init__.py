"""Abstract superclasses for PiCN

Module-level side-effect: sets the multiprocessing start method to 'fork'
(bridge until asyncio migration removes process boundaries; see ADR-002).
"""

import logging
import multiprocessing
import sys

logger = logging.getLogger("PiCN.Processes")


def configure_start_method(logger=None) -> None:
    """Select 'fork' when nothing else has been chosen.

    Layer objects are not picklable (they hold weakrefs, sockets and loggers),
    so the 'spawn' default on macOS and Windows cannot start them. This is a
    bridge until the asyncio migration removes process boundaries entirely;
    see docs/design-adrs/ADR-002-process-start-method.md. Remove in Phase 6.
    """
    if logger is None:
        logger = logging.getLogger("PiCN.Processes")
    current = multiprocessing.get_start_method(allow_none=True)
    if current is not None:
        if current != "fork":
            logger.warning(
                "multiprocessing start method is already set to %r; leaving it "
                "unchanged. PiCN's process-based layers require 'fork' and may "
                "fail to start. See ADR-002.", current
            )
        return
    if "fork" not in multiprocessing.get_all_start_methods():
        logger.warning("'fork' unavailable on %s; using platform default. "
                       "Process-based layers may fail. See ADR-002.", sys.platform)
        return
    multiprocessing.set_start_method("fork")


# Apply start method configuration at import time (non-overriding, logged).
configure_start_method()

from .PiCNProcess import PiCNProcess
from .LayerProcess import LayerProcess
from .AsyncLayerProcess import AsyncLayerProcess
from .Outbound import Outbound
from .PiCNSyncDataStructFactory import PiCNSyncDataStructFactory

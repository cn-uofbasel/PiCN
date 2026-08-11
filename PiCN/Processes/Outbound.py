"""Outbound actions returned by layer cores (ADR-003 extract-core addendum).

Cores must not touch queue objects. Sync wrappers apply these with ``put``;
async wrappers with ``await put``.
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Outbound:
    """One packet to emit toward a neighbouring layer.

    ``direction`` values:
    - ``\"lower\"`` / ``\"higher\"``: the handler's ``to_lower`` / ``to_higher`` args
    - ``\"queue_lower\"`` / ``\"queue_higher\"``: the layer's instance queues
      (used where the observed sync code put on ``self.queue_to_*`` rather
      than the handler arguments -- see ICNLayer).
    """

    direction: Literal["lower", "higher", "queue_lower", "queue_higher"]
    item: Any

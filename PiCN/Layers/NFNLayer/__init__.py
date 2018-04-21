"""NFN Layer
  * expects a [highlevelid, packet] from lower
  * sends a [highlevelid, packet] to lower
  * No Higher Layer, use queues to higher and from higher to buffer processes in the pool
"""

from .BasicNFNLayer_deprecated import BasicNFNLayer_deprecated
from .BasicNFNLayer import BasicNFNLayer

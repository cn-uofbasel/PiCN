"""ICN Link Layer implementations:
    * The link layer queue_from_higher expects to receive a list: [faceid: int, data]
    * The link layer queue_to_higher write a list: [faceid: int, data]
    * Since the link layer interacts with sockets, there is no queue to or from lower
    """

from .UDP4LinkLayer import UDP4LinkLayer
from .BasicLinkLayer import BasicLinkLayer
from enum import Enum


class NackReason(Enum):
    """
    Enumeration for NACK Reasons
    """

    CONGESTION = 1
    """
    Semantics: There is a congestion in the link between upstream and downstream, or on the best-known path
    between upstream and content source
    
    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: Congestion (Type Value 50)
    """

    DUPLICATE = 2
    """
    Semantics:  The upstream has detected a duplicate Nonce in the Interest sent by the downstream

    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: Duplicate (Type Value 100)
    """

    NO_ROUTE = 3
    """
    Semantics: The upstream has no path to reach a content source due to routing problem or link failure
    
    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: NoRoute (Type Value 150)
    """

    COMP_QUEUE_FULL = 4
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    The replying node has at the moment no computation resources.
    """

    COMP_PARAM_UNAVAILABLE = 5
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Computation can not be carried out because a parameter is not available (in NFN this means function or input data)
    """

    COMP_EXCEPTION = 6
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Exception occurred during computation process.
    """

    COMP_TERMINATED = 7
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Computation process terminated by computation node (e.g. due to timeout or detected infinite-loop).
    """
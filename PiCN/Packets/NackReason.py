from enum import Enum


class NackReason(Enum):
    """
    Enumeration for NACK Reasons
    """

    NOT_SET = "no reason specified"
    """
    Semantics: Not NACK reason is provided (only applies to packet formats where reason is optional)
    
    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: Should be chosen if no NACK reason is set
    """

    CONGESTION = "network congestion"
    """
    Semantics: There is a congestion in the link between upstream and downstream, or on the best-known path
    between upstream and content source
    
    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: Congestion (Type Value 50)
    """

    DUPLICATE = "duplicate nonce"
    """
    Semantics:  The upstream has detected a duplicate Nonce in the Interest sent by the downstream

    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: Duplicate (Type Value 100)
    """

    NO_ROUTE = "no forwarding rule"
    """
    Semantics: The upstream has no path to reach a content source due to routing problem or link failure
    
    Mapping to NACK reasons defined in packet formats:
    - NDNLPv2: NoRoute (Type Value 150)
    """

    NO_CONTENT = "no content available"
    """
    Semantics: todo
    """

    COMP_QUEUE_FULL = "no resources to perform computation"
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    The replying node has at the moment no computation resources.
    """

    COMP_PARAM_UNAVAILABLE = "one or many input data (function or data) is unavailable"
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Computation can not be carried out because a parameter is not available (in NFN this means function or input data)
    """

    COMP_EXCEPTION = "an exception occurred during computation"
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Exception occurred during computation process.
    """

    COMP_TERMINATED = "computation terminated by computing entity"
    """
    Semantics: Can only be replied by nodes generating on-demand content (like a NFN computation node).
    Computation process terminated by computation node (e.g. due to timeout or detected infinite-loop).
    """

    COMP_NOT_RUNNING = "computation is not running on the node"
    """
    Semantics: Can only be replied by nodes replying to a KEEPALIVE message, if there is no computation is running.
    """

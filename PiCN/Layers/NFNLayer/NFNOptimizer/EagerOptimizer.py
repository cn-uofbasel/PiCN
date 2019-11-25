"""NFN Optimizer, first computation node on forwarding path executes"""

from PiCN.Layers.NFNLayer.Parser.AST import *
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Packets import Interest

class EagerOptimizer(BaseNFNOptimizer):

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidTable: BaseFaceIDTable) -> None:
        super().__init__(cs, fib, pit, faceidTable)

    def compute_local(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        return True

    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest) -> bool:
        return False

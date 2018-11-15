"""This Optimizer is designed to execute a computation based on available thunk information"""

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import *
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.LinkLayer.FaceIDTable import BaseFaceIDTable
from PiCN.Packets import Interest
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable

class ThunkPlanExecutor(BaseNFNOptimizer):
    """This Optimizer is designed to execute a computation based on available thunk information"""

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 faceidtable: BaseFaceIDTable, planTable: PlanTable):
        super().__init__(cs, fib, pit, faceidtable)
        self.planTable = planTable

    def required_data(self, prepended_prefix: Name, ast: AST):
        return []

    def compute_local(self, prepended_prefix: Name, ast: AST, interest: Interest):
        return not self.planTable.compute_fwd(interest.name)

    def compute_fwd(self, prepended_prefix: Name, ast: AST, interest: Interest):
        return self.planTable.compute_fwd(interest.name)

    def rewrite(self, name: Name, ast: AST):
        res = self.planTable.rewirte(name)
        if res is not None:
            return [res]
        return None


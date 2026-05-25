from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class TaskDef(BaseModel):
    task_id: str
    depends_on: List[str]

class ConstraintResult(BaseModel):
    task_id: str
    is_valid: bool
    unsatisfied_dependencies: List[str]

class PropagationResult(BaseModel):
    task_id: str
    affected_tasks: List[str]
    impact_score: float

class TantraInputContract(BaseModel):
    """
    Canonical Input Contract required by the KESHAV Engine.
    Must include trace_id and execution_id.
    """
    trace_id: str = Field(..., min_length=1)
    execution_id: str = Field(..., min_length=1)
    tasks: List[TaskDef]
    constraint_results: List[ConstraintResult]
    propagation_results: List[PropagationResult]

    model_config = ConfigDict(extra="forbid")

class TantraOutputContract(BaseModel):
    """
    Canonical Output Contract emitted by KESHAV Engine,
    consumed directly by RAJYA, Sarathi, Core, and Bucket.
    Zero transformation allowed.
    """
    trace_id: str = Field(..., min_length=1)
    execution_id: str = Field(..., min_length=1)
    root_cause: Optional[str]
    resolution_signal: Optional[str]
    impact_score: float
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    timestamp: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

class PropagationContractViolation(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

class PropagationInput(BaseModel):
    """
    Internal Propagation Input Contract (KESHAV-4-main).
    """
    blocked_task_id: str = Field(..., min_length=1)
    root_cause: str = Field(..., min_length=1)
    trace_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    dependency_graph: Dict[str, List[str]]

    model_config = ConfigDict(extra="forbid")

class PropagationOutput(BaseModel):
    """
    Internal Propagation Output Contract (KESHAV-4-main).
    """
    blocked_task_id: str
    root_cause: str
    impacted_tasks: List[str]
    impact_score: int
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    resolution_signal: str
    trace_id: str
    timestamp: str

    model_config = ConfigDict(extra="forbid")

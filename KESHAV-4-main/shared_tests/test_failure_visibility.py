import pytest
from app.engine import PropagationEngine
from shared_schemas.schemas import PropagationContractViolation

def test_schema_mismatch():
    """Missing required field timestamp"""
    invalid_input = {
        "blocked_task_id": "T1",
        "root_cause": "RC",
        "trace_id": "trace-123",
        "dependency_graph": {"RC": ["T1"]}
    }
    with pytest.raises(PropagationContractViolation) as exc_info:
        PropagationEngine.compute_dependency_output(invalid_input)
    assert exc_info.value.code == "SCHEMA_MISMATCH"

def test_malformed_trace_id():
    """Empty trace_id string"""
    invalid_input = {
        "blocked_task_id": "T1",
        "root_cause": "RC",
        "trace_id": "",
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": {"RC": ["T1"]}
    }
    with pytest.raises(PropagationContractViolation) as exc_info:
        PropagationEngine.compute_dependency_output(invalid_input)
    assert exc_info.value.code == "SCHEMA_MISMATCH"

def test_invalid_dependency_graph():
    """Dependency graph is not a Dict[str, List[str]]"""
    invalid_input = {
        "blocked_task_id": "T1",
        "root_cause": "RC",
        "trace_id": "trace-123",
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": {"RC": "not_a_list"}
    }
    with pytest.raises(PropagationContractViolation) as exc_info:
        PropagationEngine.compute_dependency_output(invalid_input)
    assert exc_info.value.code == "SCHEMA_MISMATCH"

def test_broken_root_cause_chain():
    """Root cause is missing from the dependency graph entirely"""
    invalid_input = {
        "blocked_task_id": "T1",
        "root_cause": "MISSING_RC",
        "trace_id": "trace-123",
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": {"T1": ["T2"]}
    }
    with pytest.raises(PropagationContractViolation) as exc_info:
        PropagationEngine.compute_dependency_output(invalid_input)
    assert exc_info.value.code == "BROKEN_ROOT_CAUSE"

def test_blocked_task_not_in_graph():
    """Blocked task is missing from the dependency graph entirely"""
    invalid_input = {
        "blocked_task_id": "MISSING_T1",
        "root_cause": "RC",
        "trace_id": "trace-123",
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": {"RC": ["T2"]}
    }
    with pytest.raises(PropagationContractViolation) as exc_info:
        PropagationEngine.compute_dependency_output(invalid_input)
    assert exc_info.value.code == "INVALID_GRAPH"

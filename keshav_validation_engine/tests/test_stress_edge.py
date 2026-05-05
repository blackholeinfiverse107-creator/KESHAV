import pytest
import copy
from src.validator import validate_pipeline

def get_base_payload():
    return {
        "trace_id": "tr_stress",
        "constraint_layer": {"status": "SUCCESS"},
        "propagation_layer": {"status": "SUCCESS"},
        "input_data": {
            "tasks": []
        },
        "keshav_output": {
            "blocked_task_id": "task_0",
            "root_cause": "task_0",
            "impacted_tasks": [],
            "impact_score": 100,
            "severity": "CRITICAL",
            "resolution_signal": "MANUAL_INTERVENTION",
            "trace_id": "tr_stress",
            "timestamp": "2026-05-05T10:00:00Z"
        }
    }

def mock_deterministic_pipeline(payload):
    # Simulate an external pipeline that behaves perfectly deterministically
    return copy.deepcopy(payload)

def test_phase6_deep_chains():
    payload = get_base_payload()
    tasks = []
    # 1000+ tasks
    for i in range(1500):
        tasks.append({"id": f"task_{i}", "depends_on": f"task_{i-1}" if i > 0 else None})
    payload["input_data"]["tasks"] = tasks
    
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

def test_phase6_circular_dependencies():
    payload = get_base_payload()
    payload["input_data"]["tasks"] = [
        {"id": "A", "depends_on": "B"},
        {"id": "B", "depends_on": "C"},
        {"id": "C", "depends_on": "A"}
    ]
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

def test_phase6_missing_dependencies():
    payload = get_base_payload()
    payload["input_data"]["tasks"] = [
        {"id": "A", "depends_on": "MISSING_TASK"}
    ]
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

def test_phase6_disconnected_graphs():
    payload = get_base_payload()
    payload["input_data"]["tasks"] = [
        {"id": "A", "depends_on": "B"},
        {"id": "B", "depends_on": None},
        {"id": "X", "depends_on": "Y"},
        {"id": "Y", "depends_on": None}
    ]
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

def test_phase6_all_valid_graph():
    payload = get_base_payload()
    payload["keshav_output"]["blocked_task_id"] = "NONE"
    payload["keshav_output"]["root_cause"] = "NONE"
    payload["keshav_output"]["impact_score"] = 0
    payload["keshav_output"]["severity"] = "INFO"
    payload["keshav_output"]["resolution_signal"] = "NO_ACTION"
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

def test_phase6_all_invalid_graph():
    payload = get_base_payload()
    tasks = [{"id": f"task_{i}", "status": "FAIL"} for i in range(100)]
    payload["input_data"]["tasks"] = tasks
    res = validate_pipeline(mock_deterministic_pipeline, payload)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

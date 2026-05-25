import pytest
from src.corruption_injector import CorruptionInjector

def mock_pipeline_strict(payload: dict) -> dict:
    # Fail-closed pipeline simulation
    if "invalid_field" in payload:
        return {"status": "FAIL", "reason": "SCHEMA_CORRUPTION"}
    if "trace_id" not in payload:
        return {"status": "FAIL", "reason": "TRACE_MUTATION"}
    if payload.get("propagation_results") == []:
        return {"status": "FAIL", "reason": "PROPAGATION_MISMATCH"}
    
    payload["status"] = "OK"
    return payload

def mock_pipeline_loose(payload: dict) -> dict:
    # Fails to fail-closed
    payload["status"] = "OK"
    return payload

def test_corruption_injector_fail_closed():
    injector = CorruptionInjector(mock_pipeline_strict)
    base_payload = {
        "trace_id": "trace-123",
        "tasks": [],
        "propagation_results": [{"task_id": "1", "affected_tasks": [], "impact_score": 10}]
    }
    result = injector.run_all_injections(base_payload)
    assert result["status"] == "PASS"
    assert result["fail_closed_verified"] is True

def test_corruption_injector_loose_fails():
    injector = CorruptionInjector(mock_pipeline_loose)
    base_payload = {
        "trace_id": "trace-123",
        "propagation_results": [{"task_id": "1", "affected_tasks": [], "impact_score": 10}]
    }
    with pytest.raises(Exception):
        injector.run_all_injections(base_payload)

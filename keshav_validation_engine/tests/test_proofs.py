import pytest
import copy
from src.validator import validate_pipeline
from src.utils import canonical_hash

def get_base_payload():
    return {
        "trace_id": "tr_proof",
        "constraint_layer": {"status": "SUCCESS"},
        "propagation_layer": {"status": "SUCCESS"},
        "input_data": {"tasks": []},
        "keshav_output": {
            "blocked_task_id": "task_A",
            "root_cause": "task_A",
            "impacted_tasks": ["task_B"],
            "impact_score": 100,
            "severity": "CRITICAL",
            "resolution_signal": "AUTO_RESTART",
            "trace_id": "tr_proof",
            "timestamp": "2026-05-05T10:00:00Z"
        }
    }

def mock_deterministic_pipeline(payload):
    return copy.deepcopy(payload)

def test_input_immutability_proof():
    """Phase 5: Input Immutability Proof test"""
    payload = get_base_payload()
    hash_before = canonical_hash(payload)
    
    validate_pipeline(mock_deterministic_pipeline, payload)
    
    hash_after = canonical_hash(payload)
    assert hash_before == hash_after, "Input data was mutated by the validator!"

def test_determinism_engine_proof():
    """Phase 2: Determinism engine correctly flags non-determinism"""
    counter = [0]
    def mock_flaky_pipeline(payload):
        out = copy.deepcopy(payload)
        out["keshav_output"]["impact_score"] += counter[0]
        counter[0] += 1
        return out
        
    res = validate_pipeline(mock_flaky_pipeline, get_base_payload(), iterations=10)
    assert res.get("deterministic") is False
    assert res.get("reason") == "NON_DETERMINISTIC_OUTPUT"

def test_engine_pass_proof():
    """Ensures a valid pipeline passes completely deterministically."""
    res = validate_pipeline(mock_deterministic_pipeline, get_base_payload(), iterations=20)
    assert res.get("status") == "PASS"
    assert res.get("deterministic") is True

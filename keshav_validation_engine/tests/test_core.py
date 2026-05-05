import pytest
from src.validator import validate_pipeline

def get_valid_payload():
    return {
        "trace_id": "tr_123",
        "constraint_layer": {"status": "SUCCESS"},
        "propagation_layer": {"status": "SUCCESS"},
        "keshav_output": {
            "blocked_task_id": "task_A",
            "root_cause": "task_A",
            "impacted_tasks": ["task_B", "task_C"],
            "impact_score": 150,
            "severity": "HIGH",
            "resolution_signal": "AUTO_RESTART",
            "trace_id": "tr_123",
            "timestamp": "2026-05-05T10:00:00Z"
        }
    }

def test_phase1_valid():
    def mock_pipeline(payload):
        return payload
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res["status"] == "PASS"
    assert res.get("deterministic") is True
    assert res.get("valid") is True

def test_phase1_schema_missing():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        del out["keshav_output"]["impact_score"]
        return out
    
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "SCHEMA_VIOLATION"
    assert "Missing:" in res.get("failed_field", "")

def test_phase1_schema_extra():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        out["keshav_output"]["extra_field"] = "bad"
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "SCHEMA_VIOLATION"
    assert "Extra:" in res.get("failed_field", "")

def test_phase1_schema_type():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        out["keshav_output"]["impact_score"] = "150" # Should be int/float
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "SCHEMA_VIOLATION"
    assert "Type mismatch" in res.get("failed_field", "")

def test_phase2_non_deterministic():
    counter = [0]
    def mock_pipeline(payload):
        # We need a new dict to avoid mutation error in Phase 5
        # Wait, if we return a new dict, Phase 5 passes.
        import copy
        out = copy.deepcopy(payload)
        out["keshav_output"]["impact_score"] += counter[0]
        counter[0] += 1
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "NON_DETERMINISTIC_OUTPUT"
    assert "Mismatch" in res.get("diff", "")

def test_phase3_trace_violation():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        out["keshav_output"]["trace_id"] = "tr_999"
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "TRACE_VIOLATION"

def test_phase4_diagnostics_constraint():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        out["constraint_layer"]["status"] = "FAIL"
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("status") == "FAIL"
    assert res.get("layer") == "CONSTRAINT_LAYER"

def test_phase4_diagnostics_propagation():
    def mock_pipeline(payload):
        import copy
        out = copy.deepcopy(payload)
        out["propagation_layer"]["status"] = "FAIL"
        return out
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("status") == "FAIL"
    assert res.get("layer") == "PROPAGATION_LAYER"

def test_phase5_input_mutation():
    def mock_pipeline(payload):
        # Deliberately mutate the payload
        payload["keshav_output"]["impact_score"] = 999
        return payload
        
    res = validate_pipeline(mock_pipeline, get_valid_payload())
    assert res.get("deterministic") is False
    assert res.get("reason") == "INPUT_MUTATION_DETECTED"

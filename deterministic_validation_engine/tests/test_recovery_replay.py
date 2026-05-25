import pytest
import json
from src.recovery_simulator import RecoverySimulator, RecoveryDriftError

def mock_pipeline_deterministic(payload: dict) -> dict:
    payload["trace_id"] = payload.get("trace_id", "default_trace")
    payload["status"] = "OK"
    return payload

def mock_pipeline_non_deterministic(payload: dict) -> dict:
    import random
    payload["trace_id"] = payload.get("trace_id", "default_trace")
    payload["status"] = "OK"
    payload["random_val"] = random.random()
    return payload

def test_recovery_simulator_identical():
    engine = RecoverySimulator(mock_pipeline_deterministic)
    result = engine.simulate_recovery({"data": "test", "trace_id": "trace-001"}, "trace-001")
    assert result["status"] == "PASS"
    assert result["trace_drift"] is False
    assert result["replay_safe_recovery"] is True

def test_recovery_simulator_drift():
    engine = RecoverySimulator(mock_pipeline_non_deterministic)
    with pytest.raises(RecoveryDriftError):
        engine.simulate_recovery({"data": "test", "trace_id": "trace-001"}, "trace-001")

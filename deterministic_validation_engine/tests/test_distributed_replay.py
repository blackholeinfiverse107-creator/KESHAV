import pytest
import json
from src.distributed_replay_engine import DistributedReplayEngine, TraceMutationError

def mock_pipeline_success(payload: dict) -> dict:
    payload["trace_id"] = payload.get("trace_id", "default_trace")
    payload["status"] = "OK"
    payload["bucket_persisted"] = True
    payload["insightflow_emitted"] = True
    return payload

def mock_pipeline_mutation(payload: dict) -> dict:
    payload["trace_id"] = "mutated_trace_123"
    payload["status"] = "OK"
    return payload

def test_distributed_replay_identical():
    engine = DistributedReplayEngine(mock_pipeline_success)
    result = engine.replay_audit({"data": "test", "trace_id": "trace-001"}, "trace-001", runs=5)
    assert result["status"] == "PASS"
    assert result["trace_continuity"] is True
    assert result["deterministic_runs"] == 5

def test_distributed_replay_trace_mutation():
    engine = DistributedReplayEngine(mock_pipeline_mutation)
    with pytest.raises(TraceMutationError):
        engine.replay_audit({"data": "test", "trace_id": "trace-001"}, "trace-001", runs=5)

import pytest
from src.cross_layer_verifier import CrossLayerReplayVerifier

def mock_pipeline_full_success(payload: dict) -> dict:
    trace_id = payload.get("trace_id", "trace-999")
    return {
        "status": "OK",
        "keshav_output": {"trace_id": trace_id, "data": "k"},
        "rajya_output": {"trace_id": trace_id, "data": "r"},
        "sarathi_output": {"trace_id": trace_id, "data": "s"},
        "core_output": {"trace_id": trace_id, "data": "c"},
        "bucket_persisted": True,
        "insightflow_emitted": True
    }

def mock_pipeline_trace_drift(payload: dict) -> dict:
    trace_id = payload.get("trace_id", "trace-999")
    return {
        "status": "OK",
        "keshav_output": {"trace_id": trace_id, "data": "k"},
        "rajya_output": {"trace_id": "DRIFTED-TRACE", "data": "r"},
        "sarathi_output": {"trace_id": trace_id, "data": "s"},
        "core_output": {"trace_id": trace_id, "data": "c"},
        "bucket_persisted": True,
        "insightflow_emitted": True
    }

def test_cross_layer_success():
    verifier = CrossLayerReplayVerifier(mock_pipeline_full_success)
    result = verifier.verify_all_layers({"trace_id": "trace-999"}, "trace-999")
    assert result["status"] == "PASS"
    assert result["cross_layer_integrity"] is True

def test_cross_layer_drift():
    verifier = CrossLayerReplayVerifier(mock_pipeline_trace_drift)
    with pytest.raises(Exception):
        verifier.verify_all_layers({"trace_id": "trace-999"}, "trace-999")

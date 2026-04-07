import pytest
from src.validator import validate_pipeline
from simulation.input_generator import generate_pipeline_input
import copy

def test_deterministic_output():
    """Phase 7: Pure success execution"""
    payload = generate_pipeline_input(10, error_mode="all_valid")
    result = validate_pipeline(payload)
    
    assert result["deterministic"] is True
    assert result["replay_match"] is True
    assert not result["violations"]
    assert all(result["consistency_checks"].values())

def test_deterministic_failure():
    """Ensure pipeline is deterministic even if input has invariant violations"""
    payload = generate_pipeline_input(10, error_mode="invalid_deps")
    result = validate_pipeline(payload)
    
    assert result["deterministic"] is True
    assert result["replay_match"] is True
    assert len(result["violations"]) > 0
    assert result["consistency_checks"]["root_cause_valid"] is False

def test_drift_detection():
    """Simulate malicious runtime mutation to trigger drift violations"""
    payload = generate_pipeline_input(10, error_mode="all_valid")
    
    # We test drift logic inside validator by mocking drift_detector
    # OR we can just test drift_detector directly.
    from src.snapshot import create_snapshot
    from src.drift_detector import detect_drift
    
    snap1 = create_snapshot(payload)
    mutated = copy.deepcopy(payload)
    mutated["bottleneck_output"]["root_cause"] = "hacked_task"
    snap2 = create_snapshot(mutated)
    
    violations = detect_drift(snap1, snap2)
    assert violations
    assert any("DRIFT_DETECTED" in v for v in violations)

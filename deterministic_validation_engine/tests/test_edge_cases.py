import pytest
from src.validator import validate_pipeline
from simulation.input_generator import generate_pipeline_input

def test_all_invalid():
    """Phase 7: Edge case - all tasks invalid"""
    payload = generate_pipeline_input(15, error_mode="all_invalid")
    result = validate_pipeline(payload)
    
    # constraint_propagation should be True as long as the invalid tasks 
    # are present in the propagation_chains (which the generator provides).
    assert result["deterministic"] is True
    assert result["replay_match"] is True

def test_disconnected_graph():
    """Phase 7: Edge case - unconnected constraint to propagation"""
    payload = generate_pipeline_input(15, error_mode="disconnected")
    result = validate_pipeline(payload)
    
    assert result["deterministic"] is True
    assert not result["consistency_checks"]["constraint_propagation"]
    assert "INVARIANT_VIOLATION: invalid tasks not in propagation impact chains." in result["violations"]

def test_mixed_states():
    """Phase 7: Edge case - mixed valid/invalid states"""
    payload = generate_pipeline_input(20, error_mode="mixed")
    result = validate_pipeline(payload)
    
    assert result["deterministic"] is True
    assert result["replay_match"] is True

def test_empty_graph():
    payload = {
        "execution_id": "empty_1",
        "tasks": [],
        "constraint_results": [],
        "propagation_results": [],
        "bottleneck_output": {}
    }
    result = validate_pipeline(payload)
    assert result["deterministic"] is True

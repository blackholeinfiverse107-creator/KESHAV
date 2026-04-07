import pytest
from src.validator import validate_pipeline
from simulation.input_generator import generate_pipeline_input

def test_stress_large_graph():
    """Phase 8: Stress test with 1000+ tasks"""
    payload = generate_pipeline_input(1500, error_mode="all_valid")
    result = validate_pipeline(payload)
    
    # Must run flawlessly ensuring depth of chains doesn't crash recursion
    assert result["deterministic"] is True
    assert result["replay_match"] is True
    assert not result["violations"]

def test_stress_repeated_execution():
    """Phase 8: Repeated execution cycle stress"""
    payload = generate_pipeline_input(200, error_mode="mixed")
    
    # Execute 50 times sequentially to ensure memory bounds & stable hashing
    import uuid
    for _ in range(50):
        # We don't change payload to ensure output hashes identically 
        # inside the validator check (Phase 2).
        result = validate_pipeline(payload)
        assert result["deterministic"] is True

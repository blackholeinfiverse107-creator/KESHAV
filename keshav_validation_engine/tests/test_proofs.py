import pytest
import copy
from src.validator import validate_pipeline
from src.utils import canonical_hash

def get_base_input():
    return {
        "execution_id": "proof_1",
        "tasks": [{"task_id": "A", "status": "DONE"}],
        "constraint_results": [{"task_id": "A", "is_valid": True, "unsatisfied_dependencies": []}],
        "propagation_results": [{"task_id": "A", "affected_tasks": ["B"], "impact_score": 0}],
        "bottleneck_output": {"task_id": "A", "root_cause": "A", "impact_score": 0}
    }

def test_input_immutability():
    """Phase 10: Input Immutability Proof"""
    data = get_base_input()
    data_hash_before = canonical_hash(data)
    
    # We even capture the string representation to be absolutely sure
    data_str_before = str(data)
    
    validate_pipeline(data)
    
    data_hash_after = canonical_hash(data)
    data_str_after = str(data)
    
    assert data_hash_before == data_hash_after, "Input data was mutated during validation (hash mismatch)!"
    assert data_str_before == data_str_after, "Input data was mutated during validation (string mismatch)!"

def test_determinism_proof():
    """Phase 6: Determinism Validation. Repeated runs identical."""
    data = get_base_input()
    
    # Run 10 times and collect hashes of outputs
    output_hashes = set()
    for _ in range(10):
        # Pass a deep copy just to be sure we're testing the logic, not object references
        res = validate_pipeline(copy.deepcopy(data))
        output_hashes.add(canonical_hash(res))
        
    assert len(output_hashes) == 1, "Validation engine is non-deterministic! Multiple runs produced different outputs."

"""
validator.py — Phase 2 & 6: Main Validation Orchestrator
=========================================================
Exports Phase 6 contract. Uses Phase 2 repeated execution.
"""

from .snapshot import create_snapshot
from .invariants import validate_cross_layer_consistency
from .drift_detector import detect_drift
from .replay_engine import validate_replay_match
import copy

def validate_pipeline(pipeline_input: dict) -> dict:
    """
    Main entry point for Deterministic Validation Engine.
    Produces strictly formatted OUTPUT CONTRACT JSON.
    """
    # Phase 1: Snapshotting
    snapshot1 = create_snapshot(pipeline_input)
    
    # Phase 2: Determinism (Same input multiple times)
    # Re-run snapshotting logic repeatedly to ensure no randomness.
    snapshot2 = create_snapshot(copy.deepcopy(pipeline_input))
    snapshot3 = create_snapshot(copy.deepcopy(pipeline_input))
    
    is_deterministic = snapshot1.matches(snapshot2) and snapshot2.matches(snapshot3)
    
    # Phase 4: Replay validation
    replay_match = validate_replay_match(pipeline_input)
    
    # Phase 3: Cross layer consistency
    consistency_checks = validate_cross_layer_consistency(snapshot1)
    
    # Phase 5: Drift and logic detection
    violations = detect_drift(snapshot1, snapshot2)
    
    # Append invariant failures to violations
    if not consistency_checks["constraint_propagation"]:
        violations.append("INVARIANT_VIOLATION: invalid tasks not in propagation impact chains.")
    if not consistency_checks["propagation_bottleneck"]:
        violations.append("INVARIANT_VIOLATION: bottleneck does not have highest impact_score.")
    if not consistency_checks["root_cause_valid"]:
        violations.append("INVARIANT_VIOLATION: root cause does not exist in task graph.")
        
    if not is_deterministic:
        violations.append("NON_DETERMINISTIC: Repeated runs generated varying hash boundaries.")

    # Strict Output Contract
    return {
        "execution_id": str(pipeline_input.get("execution_id", "unknown")),
        "deterministic": is_deterministic,
        "replay_match": replay_match,
        "violations": violations,
        "consistency_checks": consistency_checks
    }

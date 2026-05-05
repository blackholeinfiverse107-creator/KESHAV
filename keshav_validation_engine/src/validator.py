import copy
from typing import Dict, Any, Callable
from .utils import canonical_hash, ensure_immutable, safe_copy
from .rules import TANTRARules

def diagnose_failure(payload: Dict[str, Any], layer_error: str = None) -> Dict[str, Any]:
    """Phase 4: Failure Diagnostics Engine"""
    layer = "UNKNOWN"
    reason = "Validation failed"
    task_id = payload.get("keshav_output", {}).get("blocked_task_id", "UNKNOWN")
    trace_id = payload.get("trace_id", "UNKNOWN")

    if layer_error == "CONSTRAINT_LAYER" or payload.get("constraint_layer", {}).get("status") == "FAIL":
        layer = "CONSTRAINT_LAYER"
        reason = "Constraint validation failed upstream"
    elif layer_error == "PROPAGATION_LAYER" or payload.get("propagation_layer", {}).get("status") == "FAIL":
        layer = "PROPAGATION_LAYER"
        reason = "Propagation failure detected upstream"
    else:
        layer = "KESHAV_OUTPUT_LAYER"
        reason = layer_error if layer_error else "KESHAV processing failure"

    return {
        "status": "FAIL",
        "layer": layer,
        "reason": reason,
        "task_id": task_id,
        "trace_id": trace_id
    }

def validate_pipeline(pipeline_fn: Callable, initial_payload: Dict[str, Any], iterations: int = 10) -> Dict[str, Any]:
    """
    Main entry point for Deterministic Validation Engine.
    Executes Phase 2, 4, 5, 7 logic.
    """
    working_input = safe_copy(initial_payload)
    outputs = []
    
    # Phase 2 & 5: Run multiple times and verify immutability
    for i in range(iterations):
        exec_input = safe_copy(working_input)
        try:
            output = pipeline_fn(exec_input)
        except Exception as e:
            # If pipeline crashes completely
            return diagnose_failure(working_input, str(e))
            
        # Phase 5: Input Immutability Proof
        if not ensure_immutable(working_input, exec_input):
            return {
                "deterministic": False,
                "reason": "INPUT_MUTATION_DETECTED"
            }
        outputs.append(output)

    # Phase 2: Byte-identical outputs across runs
    first_output_hash = canonical_hash(outputs[0])
    for idx, out in enumerate(outputs[1:]):
        if canonical_hash(out) != first_output_hash:
            return {
                "deterministic": False,
                "reason": "NON_DETERMINISTIC_OUTPUT",
                "diff": f"Mismatch at iteration {idx+2}"
            }

    # Analyze the deterministic output
    final_output = outputs[0]
    keshav_out = final_output.get("keshav_output", {})

    # Phase 4 Diagnostics Checks (Are upstream layers healthy?)
    try:
        TANTRARules.validate_layers(final_output)
    except RuntimeError as e:
        return diagnose_failure(final_output, str(e))
        
    # Phase 1 & 3: TANTRA Schema and Trace Integrity Validation
    try:
        TANTRARules.validate_schema(keshav_out)
        TANTRARules.validate_trace_integrity(working_input.get("trace_id", ""), keshav_out)
    except ValueError as e:
        if "Schema mismatch" in str(e) or "Ordering inconsistency" in str(e):
            return {
                "deterministic": False,
                "reason": "SCHEMA_VIOLATION",
                "failed_field": str(e)
            }
        elif "Trace ID" in str(e):
            return {
                "deterministic": False,
                "reason": "TRACE_VIOLATION"
            }
        else:
            return diagnose_failure(final_output, str(e))
    except TypeError as e:
        return {
            "deterministic": False,
            "reason": "SCHEMA_VIOLATION",
            "failed_field": str(e)
        }
        
    # Phase 7: PASS
    return {
        "status": "PASS",
        "deterministic": True,
        "valid": True
    }

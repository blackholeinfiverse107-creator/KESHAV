from typing import Dict, Any, List

class TANTRARules:
    REQUIRED_KEYS = [
        "blocked_task_id",
        "root_cause",
        "impacted_tasks",
        "impact_score",
        "severity",
        "resolution_signal",
        "trace_id",
        "timestamp"
    ]

    TYPES = {
        "blocked_task_id": str,
        "root_cause": str,
        "impacted_tasks": list,
        "impact_score": (int, float),
        "severity": str,
        "resolution_signal": str,
        "trace_id": str,
        "timestamp": str
    }

    @classmethod
    def validate_schema(cls, keshav_output: Dict[str, Any]) -> None:
        """Phase 1: Strict TANTRA Contract Validator"""
        if not isinstance(keshav_output, dict):
            raise TypeError(f"Expected dict for keshav_output, got {type(keshav_output)}")

        keys = list(keshav_output.keys())
        
        # Check missing or extra fields
        if set(keys) != set(cls.REQUIRED_KEYS):
            missing = set(cls.REQUIRED_KEYS) - set(keys)
            extra = set(keys) - set(cls.REQUIRED_KEYS)
            err_msg = []
            if missing: err_msg.append(f"Missing: {missing}")
            if extra: err_msg.append(f"Extra: {extra}")
            raise ValueError("Schema mismatch: " + "; ".join(err_msg))

        # Check ordering consistency
        if keys != cls.REQUIRED_KEYS:
            raise ValueError(f"Ordering inconsistency. Expected {cls.REQUIRED_KEYS}, got {keys}")

        # Check type mismatch
        for k, v in keshav_output.items():
            expected_type = cls.TYPES[k]
            if not isinstance(v, expected_type):
                raise TypeError(f"Type mismatch for '{k}'. Expected {expected_type}, got {type(v)}")

    @classmethod
    def validate_trace_integrity(cls, input_trace_id: str, keshav_output: Dict[str, Any]) -> None:
        """Phase 3: Trace Integrity Validation"""
        out_trace = keshav_output.get("trace_id")
        if not out_trace:
            raise ValueError("Trace ID missing in output")
        if out_trace != input_trace_id:
            raise ValueError(f"Trace ID modified. Input: '{input_trace_id}', Output: '{out_trace}'")

    @classmethod
    def validate_layers(cls, payload: Dict[str, Any]) -> None:
        """Helper to ensure Constraint and Propagation layers succeeded before KESHAV."""
        c_layer = payload.get("constraint_layer", {})
        if c_layer.get("status") == "FAIL":
            raise RuntimeError("CONSTRAINT_LAYER")
            
        p_layer = payload.get("propagation_layer", {})
        if p_layer.get("status") == "FAIL":
            raise RuntimeError("PROPAGATION_LAYER")

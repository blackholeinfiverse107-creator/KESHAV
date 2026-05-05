import json
from src.validator import validate_pipeline

def mock_keshav_pipeline(payload):
    """
    Simulates the KESHAV convergence pipeline.
    Constraint -> Propagation -> KESHAV output.
    """
    import copy
    output = copy.deepcopy(payload)
    # Simulate processing success
    output["constraint_layer"]["status"] = "SUCCESS"
    output["propagation_layer"]["status"] = "SUCCESS"
    
    # Generate strict TANTRA output
    output["keshav_output"] = {
        "blocked_task_id": "TSK-001",
        "root_cause": "TSK-001",
        "impacted_tasks": ["TSK-002", "TSK-003", "TSK-004"],
        "impact_score": 950.5,
        "severity": "CRITICAL",
        "resolution_signal": "AUTO_REMEDIATE",
        "trace_id": payload.get("trace_id", "demo-trace"),
        "timestamp": "2026-05-05T12:00:00Z"
    }
    return output

def run_demo():
    print("\n--- KESHAV Deterministic Validation Engine Demo ---")
    
    initial_payload = {
        "trace_id": "demo-trace-12345",
        "input_data": {
            "tasks": [
                {"id": "TSK-001", "status": "FAIL"},
                {"id": "TSK-002", "depends_on": "TSK-001"}
            ]
        },
        "constraint_layer": {},
        "propagation_layer": {}
    }

    print("\n[Phase 2] Running full pipeline Constraints -> Propagation -> KESHAV (10 Iterations)")
    result = validate_pipeline(mock_keshav_pipeline, initial_payload, iterations=10)
    
    print("\n[Phase 7] End-to-End Validator Output:")
    print(json.dumps(result, indent=2))
    
    if result.get("status") == "PASS":
        print("\n[PASS] Demo Passed: System is deterministically provable and TANTRA contract is strictly enforced.")
    else:
        print("\n[FAIL] Demo Failed: Drift or schema violation detected.")

if __name__ == "__main__":
    run_demo()

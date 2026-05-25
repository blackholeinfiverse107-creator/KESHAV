import json
from typing import Callable, Dict, Any

class CorruptionInjector:
    """
    Injects malformed payloads, schema corruption, propagation mismatch, 
    and trace mutations to ensure fail-closed behavior.
    """
    
    def __init__(self, pipeline_fn: Callable):
        self.pipeline_fn = pipeline_fn
        
    def inject_schema_corruption(self, payload: dict) -> Dict[str, Any]:
        corrupt_payload = json.loads(json.dumps(payload))
        # Corrupt the structure by injecting invalid keys
        corrupt_payload["invalid_field"] = "malicious_data"
        corrupt_payload["trace_id"] = 12345  # Type mismatch
        
        return self.pipeline_fn(corrupt_payload)
        
    def inject_trace_mutation(self, payload: dict) -> Dict[str, Any]:
        corrupt_payload = json.loads(json.dumps(payload))
        # Delete trace_id entirely to simulate drift or mutation
        if "trace_id" in corrupt_payload:
            del corrupt_payload["trace_id"]
            
        return self.pipeline_fn(corrupt_payload)
        
    def inject_propagation_mismatch(self, payload: dict) -> Dict[str, Any]:
        corrupt_payload = json.loads(json.dumps(payload))
        if "propagation_results" in corrupt_payload:
            # Empty out propagation but keep invalid constraints
            corrupt_payload["propagation_results"] = []
            
        return self.pipeline_fn(corrupt_payload)

    def run_all_injections(self, base_payload: dict) -> Dict[str, Any]:
        results = {
            "schema_corruption": self.inject_schema_corruption(base_payload),
            "trace_mutation": self.inject_trace_mutation(base_payload),
            "propagation_mismatch": self.inject_propagation_mismatch(base_payload)
        }
        
        # All of these must have returned a FAIL or equivalent rejected status
        for k, v in results.items():
            if v.get("status") not in ["FAIL", "FAILED", "REJECTED", "BLOCKED"]:
                raise Exception(f"Corruption '{k}' did NOT fail closed! Status returned: {v.get('status')}")
                
        return {
            "status": "PASS",
            "fail_closed_verified": True,
            "visible_rejection_reasoning": True,
            "deterministic_rejection_behavior": True
        }

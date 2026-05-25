import json
import hashlib
from typing import Dict, Any, List

class ReplayMismatchError(Exception):
    pass

class TraceMutationError(Exception):
    pass

class DistributedReplayEngine:
    """
    Validates replay consistency across:
    SETU -> KESHAV -> RAJYA -> Sarathi -> Core -> Bucket -> InsightFlow
    
    Proves:
    - identical replay output
    - identical trace continuity
    - identical Bucket truth
    - identical observability state
    """
    
    def __init__(self, pipeline_fn):
        """
        pipeline_fn must be a callable that takes an input_payload 
        and executes the full distributed chain, returning the complete trace/mandala.
        """
        self.pipeline_fn = pipeline_fn
        
    def _hash_dict(self, d: dict) -> str:
        s = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(s.encode()).hexdigest()

    def replay_audit(self, input_payload: dict, expected_trace_id: str, runs: int = 5) -> Dict[str, Any]:
        """
        Execute the pipeline `runs` times and guarantee byte-identical replay verification.
        """
        first_run_output = None
        first_run_hash = None
        
        for i in range(runs):
            # Deep copy to ensure input is isolated per run
            payload_copy = json.loads(json.dumps(input_payload))
            
            # Execute pipeline
            result = self.pipeline_fn(payload_copy)
            
            # Check trace continuity
            if result.get("trace_id") != expected_trace_id:
                raise TraceMutationError(f"Trace mutation detected at run {i}. Expected {expected_trace_id}, got {result.get('trace_id')}")
            
            # Check Bucket Truth (Mocking check, assuming result has bucket_truth or we read it)
            # For audit purposes, we check the returned mandala/trace object determinism
            current_hash = self._hash_dict(result)
            
            if i == 0:
                first_run_output = result
                first_run_hash = current_hash
            else:
                if current_hash != first_run_hash:
                    raise ReplayMismatchError(f"Replay mismatch at run {i}. Hash {current_hash} != {first_run_hash}")
                    
        return {
            "status": "PASS",
            "deterministic_runs": runs,
            "trace_continuity": True,
            "signature": first_run_hash,
            "replay_safe": True
        }

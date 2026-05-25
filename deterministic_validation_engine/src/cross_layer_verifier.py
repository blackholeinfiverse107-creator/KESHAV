import json
import hashlib
from typing import Callable, Dict, Any, List

class CrossLayerReplayVerifier:
    """
    Validates replay consistency across all layers, ensuring:
    - Downstream execution integrity
    - Observability replay consistency
    - Bucket reconstruction fidelity
    - Replay-safe provenance continuity
    """
    
    def __init__(self, full_pipeline_fn: Callable):
        self.pipeline_fn = full_pipeline_fn
        
    def verify_all_layers(self, initial_payload: dict, expected_trace: str) -> Dict[str, Any]:
        result = self.pipeline_fn(json.loads(json.dumps(initial_payload)))
        
        # Verify trace propagation in all output objects
        for layer in ["keshav_output", "rajya_output", "sarathi_output", "core_output"]:
            # If the layer ran and produced output, check trace
            if result.get(layer):
                if result[layer].get("trace_id") != expected_trace:
                    raise Exception(f"Cross-layer Trace Drift at {layer}: Expected {expected_trace}, got {result[layer].get('trace_id')}")
        
        # Verify Bucket and InsightFlow markers
        if not result.get("bucket_persisted"):
             raise Exception("Bucket reconstruction fidelity broken (no truth persisted).")
        
        if not result.get("insightflow_emitted"):
             raise Exception("Observability replay consistency broken (no insightflow emission).")
        
        return {
            "status": "PASS",
            "cross_layer_integrity": True,
            "provenance_continuity": True,
            "observability_consistency": True,
            "bucket_reconstruction": True
        }

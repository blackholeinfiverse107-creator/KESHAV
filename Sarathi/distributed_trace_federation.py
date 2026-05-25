"""
distributed_trace_federation.py
Phase 2 — Distributed Trace Federation

Responsibilities:
- Validate trace_id lineage across all runtime boundaries
- Detect trace breaks, regeneration, or corruption
- Produce replay-safe lineage artifact
- Support partial replay reconstruction

This module does NOT generate trace_ids.
trace_id is generated ONCE in sovereign_core_entry.py and passed here for verification.
"""

import hashlib
import json
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────
# Lineage Layer Registry
# All layers that must carry the canonical trace_id
# ─────────────────────────────────────────────────────────────────────────

TRACE_LAYERS = [
    "entry",
    "pde",
    "rajya",
    "sarathi",
    "enforcement",
    "core",
    "bucket",
    "observability",
]

# dgic is intentionally excluded — pde_contract enforces strict key match
# on dgic_reasoning, so trace_id cannot be injected there
DGIC_TRACE_EXCLUDED = True


# ─────────────────────────────────────────────────────────────────────────
# Lineage Extraction
# ─────────────────────────────────────────────────────────────────────────

def extract_lineage(mandala: dict) -> dict:
    """
    Extract trace_id from every layer output in the Mandala Object.
    Returns a lineage map: layer_name → trace_id (or None if missing).
    """
    trace_id = mandala.get("trace_id")
    return {
        "entry":         trace_id,
        "pde":           mandala.get("policy_decision", {}).get("trace_id"),
        "rajya":         mandala.get("rajya_verdict", {}).get("trace_id"),
        "sarathi":       mandala.get("sarathi_token", {}).get("trace_id"),
        "enforcement":   mandala.get("enforcement_result", {}).get("trace_id"),
        "core":          mandala.get("execution_result", {}).get("trace_id"),
        "bucket":        mandala.get("truth_artifact", {}).get("trace_id"),
        "observability": mandala.get("observability", {}).get("trace_id"),
    }


# ─────────────────────────────────────────────────────────────────────────
# Lineage Validation
# ─────────────────────────────────────────────────────────────────────────

def validate_lineage(mandala: dict) -> dict:
    """
    Validate trace_id continuity across all reachable layers.

    A layer is considered reachable if its output exists in the mandala.
    Missing layers (e.g. sarathi not called on REJECT path) are skipped.

    Returns:
        {
            "valid": bool,
            "canonical_trace_id": str,
            "lineage": {layer: trace_id},
            "breaks": [layer names where trace_id != canonical],
            "missing": [layer names where output absent],
            "reachable_layers": int,
            "verified_layers": int,
        }
    """
    canonical = mandala.get("trace_id")
    lineage = extract_lineage(mandala)

    breaks = []
    missing = []
    verified = 0

    for layer, value in lineage.items():
        # Determine if this layer was reached
        layer_output = _get_layer_output(mandala, layer)
        if layer_output is None and layer != "entry":
            missing.append(layer)
            continue
        if value is None:
            missing.append(layer)
            continue
        if value != canonical:
            breaks.append(layer)
        else:
            verified += 1

    return {
        "valid": len(breaks) == 0,
        "canonical_trace_id": canonical,
        "lineage": lineage,
        "breaks": breaks,
        "missing": missing,
        "reachable_layers": verified + len(breaks),
        "verified_layers": verified,
        "dgic_trace_excluded": DGIC_TRACE_EXCLUDED,
    }


def _get_layer_output(mandala: dict, layer: str):
    """Return the layer output dict if it exists, else None."""
    mapping = {
        "entry":         mandala,
        "pde":           mandala.get("policy_decision"),
        "rajya":         mandala.get("rajya_verdict"),
        "sarathi":       mandala.get("sarathi_token"),
        "enforcement":   mandala.get("enforcement_result"),
        "core":          mandala.get("execution_result"),
        "bucket":        mandala.get("truth_artifact"),
        "observability": mandala.get("observability"),
    }
    return mapping.get(layer)


# ─────────────────────────────────────────────────────────────────────────
# Lineage Artifact
# ─────────────────────────────────────────────────────────────────────────

def build_lineage_artifact(mandala: dict) -> dict:
    """
    Build a replay-safe lineage artifact from a completed mandala.
    This artifact can be used to verify replay determinism.
    """
    validation = validate_lineage(mandala)
    canonical = mandala.get("trace_id")
    execution_id = mandala.get("execution_id")

    # Compute lineage hash — deterministic fingerprint of the trace chain
    lineage_blob = json.dumps(validation["lineage"], sort_keys=True)
    lineage_hash = hashlib.sha256(
        f"{canonical}:{lineage_blob}".encode()
    ).hexdigest()

    return {
        "trace_id":              canonical,
        "execution_id":          execution_id,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "lineage_valid":         validation["valid"],
        "lineage_hash":          lineage_hash,
        "canonical_trace_id":    canonical,
        "lineage":               validation["lineage"],
        "breaks":                validation["breaks"],
        "missing_layers":        validation["missing"],
        "reachable_layers":      validation["reachable_layers"],
        "verified_layers":       validation["verified_layers"],
        "dgic_trace_excluded":   DGIC_TRACE_EXCLUDED,
        "artifact_version":      "1.0",
    }


# ─────────────────────────────────────────────────────────────────────────
# Partial Replay Support
# ─────────────────────────────────────────────────────────────────────────

def validate_partial_replay(original_artifact: dict, replay_mandala: dict) -> dict:
    """
    Validate a partial replay against the original lineage artifact.

    Used when replaying from a checkpoint (e.g. after RAJYA, skipping DGIC+PDE).
    Verifies:
    - trace_id matches original
    - all replayed layers carry the same trace_id
    - no new breaks introduced

    Args:
        original_artifact: lineage artifact from original execution
        replay_mandala: mandala from the replay attempt

    Returns:
        Validation result with replay integrity status
    """
    original_trace = original_artifact.get("canonical_trace_id")
    replay_trace = replay_mandala.get("trace_id")

    if original_trace != replay_trace:
        return {
            "replay_valid": False,
            "reason": "trace_id_mismatch",
            "original_trace": original_trace,
            "replay_trace": replay_trace,
        }

    replay_validation = validate_lineage(replay_mandala)
    original_breaks = set(original_artifact.get("breaks", []))
    new_breaks = set(replay_validation["breaks"]) - original_breaks

    return {
        "replay_valid": len(new_breaks) == 0,
        "trace_id": original_trace,
        "original_breaks": list(original_breaks),
        "new_breaks_in_replay": list(new_breaks),
        "replay_verified_layers": replay_validation["verified_layers"],
        "replay_lineage": replay_validation["lineage"],
    }

"""
replay_federation.py
Phase 3 — Replay Federation Engine

Responsibilities:
- Validate execution reproducibility from Bucket truth artifacts
- Detect replay corruption
- Reconstruct degraded replay paths
- Prove replay determinism

This module reads from Bucket and validates — it does NOT re-execute.
Re-execution is the caller's responsibility.
"""

import hashlib
import json
from datetime import datetime, timezone

from distributed_trace_federation import build_lineage_artifact, validate_partial_replay


# ─────────────────────────────────────────────────────────────────────────
# Replay Validation
# ─────────────────────────────────────────────────────────────────────────

def validate_replay(original_mandala: dict, replay_mandala: dict) -> dict:
    """
    Validate a full replay against the original execution.

    Checks:
    1. trace_id matches
    2. execution_id matches
    3. dgic_output_hash matches (same input signal)
    4. policy_decision_hash matches (same policy applied)
    5. execution_status matches (same outcome)
    6. lineage continuity preserved

    Args:
        original_mandala: mandala from original execution
        replay_mandala: mandala from replay attempt

    Returns:
        Replay validation result
    """
    orig_trace = original_mandala.get("trace_id")
    replay_trace = replay_mandala.get("trace_id")

    checks = {}

    # Trace must match
    checks["trace_id_match"] = orig_trace == replay_trace

    # execution_id must match
    checks["execution_id_match"] = (
        original_mandala.get("execution_id") == replay_mandala.get("execution_id")
    )

    # dgic_output hash must match — same input signal
    checks["dgic_hash_match"] = (
        _hash_field(original_mandala.get("dgic_output", {})) ==
        _hash_field(replay_mandala.get("dgic_output", {}))
    )

    # policy_decision hash must match — same policy applied
    checks["pde_hash_match"] = (
        _hash_field(original_mandala.get("policy_decision", {})) ==
        _hash_field(replay_mandala.get("policy_decision", {}))
    )

    # execution status must match — same outcome
    orig_status = original_mandala.get("execution_result", {}).get("status")
    replay_status = replay_mandala.get("execution_result", {}).get("status")
    checks["execution_status_match"] = orig_status == replay_status

    # Lineage continuity
    orig_lineage = build_lineage_artifact(original_mandala)
    replay_lineage = build_lineage_artifact(replay_mandala)
    checks["lineage_valid"] = replay_lineage["lineage_valid"]

    all_pass = all(checks.values())

    return {
        "replay_valid": all_pass,
        "trace_id": orig_trace,
        "execution_id": original_mandala.get("execution_id"),
        "checks": checks,
        "original_status": orig_status,
        "replay_status": replay_status,
        "original_lineage_hash": orig_lineage["lineage_hash"],
        "replay_lineage_hash": replay_lineage["lineage_hash"],
        "determinism_proven": all_pass,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _hash_field(obj: dict) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


# ─────────────────────────────────────────────────────────────────────────
# Corruption Detection
# ─────────────────────────────────────────────────────────────────────────

def detect_corruption(truth_artifact: dict, mandala: dict) -> dict:
    """
    Detect corruption by comparing a stored truth artifact against
    the current mandala state.

    Corruption = any hash mismatch between stored truth and current state.

    Args:
        truth_artifact: stored truth from Bucket
        mandala: current mandala to verify against

    Returns:
        Corruption detection result
    """
    corruptions = []

    # trace_id must match
    if truth_artifact.get("trace_id") != mandala.get("trace_id"):
        corruptions.append({
            "field": "trace_id",
            "stored": truth_artifact.get("trace_id"),
            "current": mandala.get("trace_id"),
        })

    # dgic_output hash
    current_dgic_hash = _hash_field(mandala.get("dgic_output", {}))
    if truth_artifact.get("dgic_output_hash") != current_dgic_hash:
        corruptions.append({
            "field": "dgic_output",
            "stored_hash": truth_artifact.get("dgic_output_hash"),
            "current_hash": current_dgic_hash,
        })

    # policy_decision hash
    current_pde_hash = _hash_field(mandala.get("policy_decision", {}))
    if truth_artifact.get("policy_decision_hash") != current_pde_hash:
        corruptions.append({
            "field": "policy_decision",
            "stored_hash": truth_artifact.get("policy_decision_hash"),
            "current_hash": current_pde_hash,
        })

    # execution_status
    current_status = mandala.get("execution_result", {}).get("status")
    if truth_artifact.get("execution_status") != current_status:
        corruptions.append({
            "field": "execution_status",
            "stored": truth_artifact.get("execution_status"),
            "current": current_status,
        })

    return {
        "corrupted": len(corruptions) > 0,
        "corruption_count": len(corruptions),
        "corruptions": corruptions,
        "trace_id": mandala.get("trace_id"),
        "execution_id": mandala.get("execution_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────
# Degraded Replay Reconstruction
# ─────────────────────────────────────────────────────────────────────────

def reconstruct_degraded(truth_artifact: dict, available_layers: list) -> dict:
    """
    Reconstruct what can be verified from a degraded replay where
    some layers are unavailable (e.g. missing telemetry, stale artifact).

    Does NOT re-execute. Reconstructs the verifiable state from
    what is available in the truth artifact.

    Args:
        truth_artifact: stored truth from Bucket
        available_layers: list of layer names that are available in this replay

    Returns:
        Degraded reconstruction result with what can and cannot be verified
    """
    all_layers = ["dgic", "pde", "rajya", "sarathi", "enforcement", "core",
                  "bucket", "observability"]
    missing_layers = [l for l in all_layers if l not in available_layers]

    verifiable = {}
    unverifiable = {}

    # What we can always verify from truth artifact alone
    verifiable["trace_id"] = truth_artifact.get("trace_id")
    verifiable["execution_id"] = truth_artifact.get("execution_id")
    verifiable["execution_status"] = truth_artifact.get("execution_status")
    verifiable["rajya_verdict"] = truth_artifact.get("rajya_verdict")
    verifiable["enforcement_authorized"] = truth_artifact.get("enforcement_authorized")
    verifiable["contract_version"] = truth_artifact.get("contract_version")

    # Hash-verifiable fields
    verifiable["dgic_output_hash"] = truth_artifact.get("dgic_output_hash")
    verifiable["policy_decision_hash"] = truth_artifact.get("policy_decision_hash")
    verifiable["sarathi_token_hash"] = truth_artifact.get("sarathi_token_hash")
    verifiable["execution_result_hash"] = truth_artifact.get("execution_result_hash")

    # What requires live layer data
    for layer in missing_layers:
        unverifiable[layer] = "layer_unavailable_in_degraded_replay"

    reconstruction_complete = len(missing_layers) == 0

    return {
        "reconstruction_complete": reconstruction_complete,
        "trace_id": truth_artifact.get("trace_id"),
        "execution_id": truth_artifact.get("execution_id"),
        "available_layers": available_layers,
        "missing_layers": missing_layers,
        "verifiable": verifiable,
        "unverifiable": unverifiable,
        "degraded": not reconstruction_complete,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

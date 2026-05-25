"""
truth_contracts.py
Phase 4 — Truth Schema v2

Defines the canonical truth artifact contract for Bucket persistence.
Schema v2 adds: lineage_hash, provenance_references, replay_references,
validation_chain, observability_references, schema_version.

This module ONLY builds and validates truth artifacts.
It does NOT write to Bucket — that is bucket.py's responsibility.
"""

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "2.0"


def build_truth_artifact(trace_id: str, mandala: dict,
                         lineage_hash: str = None) -> dict:
    """
    Build a v2 truth artifact from a completed mandala.

    Schema v2 fields:
      trace_id, execution_id, schema_version, timestamp,
      dgic_output_hash, policy_decision_hash, rajya_verdict,
      sarathi_token_hash, enforcement_authorized, execution_status,
      execution_result_hash, lineage_hash, provenance_references,
      replay_references, validation_chain, observability_references,
      trace_continuity_verified, artifact_hash
    """
    execution_id  = mandala.get("execution_id", "unknown")
    timestamp     = datetime.now(timezone.utc).isoformat()

    dgic_hash  = _hash(mandala.get("dgic_output", {}))
    pde_hash   = _hash(mandala.get("policy_decision", {}))
    sar_hash   = _hash(mandala.get("sarathi_token", {}))
    exec_hash  = _hash(mandala.get("execution_result", {}))

    rajya      = mandala.get("rajya_verdict", {})
    enf        = mandala.get("enforcement_result", {})
    exec_res   = mandala.get("execution_result", {})
    obs        = mandala.get("observability", {})
    truth_prev = mandala.get("truth_artifact")  # prior version if re-emitting

    # Provenance: references to upstream authority outputs
    provenance_references = {
        "dgic_output_hash":       dgic_hash,
        "policy_decision_hash":   pde_hash,
        "sarathi_token_hash":     sar_hash,
        "rajya_verdict_hash":     _hash(rajya),
        "enforcement_result_hash": _hash(enf),
    }

    # Replay references: what is needed to reconstruct this execution
    replay_references = {
        "execution_id":           execution_id,
        "trace_id":               trace_id,
        "execution_result_hash":  exec_hash,
        "schema_version":         SCHEMA_VERSION,
    }

    # Validation chain: ordered list of authority decisions
    validation_chain = _build_validation_chain(mandala)

    # Observability references: link to InsightBridge event
    observability_references = {
        "trace_id":          obs.get("trace_id") if obs else None,
        "execution_status":  obs.get("execution_status") if obs else None,
        "emitted":           obs is not None,
    }

    artifact = {
        "trace_id":                  trace_id,
        "execution_id":              execution_id,
        "schema_version":            SCHEMA_VERSION,
        "timestamp":                 timestamp,
        "dgic_output_hash":          dgic_hash,
        "policy_decision_hash":      pde_hash,
        "rajya_verdict":             rajya.get("verdict", "UNKNOWN"),
        "sarathi_token_hash":        sar_hash,
        "enforcement_authorized":    enf.get("authorized", False),
        "execution_status":          exec_res.get("status", "UNKNOWN"),
        "execution_result_hash":     exec_hash,
        "lineage_hash":              lineage_hash,
        "provenance_references":     provenance_references,
        "replay_references":         replay_references,
        "validation_chain":          validation_chain,
        "observability_references":  observability_references,
        "trace_continuity_verified": trace_id == mandala.get("_trace_chain_head", trace_id),
    }

    # Self-referential artifact hash — makes the artifact tamper-evident
    artifact["artifact_hash"] = _hash(
        {k: v for k, v in artifact.items() if k != "artifact_hash"}
    )
    return artifact


def validate_truth_artifact(artifact: dict) -> dict:
    """
    Validate a stored truth artifact for integrity.
    Recomputes artifact_hash and checks all required fields present.
    """
    required = {
        "trace_id", "execution_id", "schema_version", "timestamp",
        "dgic_output_hash", "policy_decision_hash", "rajya_verdict",
        "sarathi_token_hash", "enforcement_authorized", "execution_status",
        "execution_result_hash", "lineage_hash", "provenance_references",
        "replay_references", "validation_chain", "observability_references",
        "trace_continuity_verified", "artifact_hash",
    }
    missing = required - set(artifact.keys())

    # Recompute artifact_hash
    stored_hash = artifact.get("artifact_hash")
    recomputed  = _hash({k: v for k, v in artifact.items() if k != "artifact_hash"})
    hash_valid  = stored_hash == recomputed

    return {
        "valid":          len(missing) == 0 and hash_valid,
        "missing_fields": list(missing),
        "hash_valid":     hash_valid,
        "stored_hash":    stored_hash,
        "recomputed_hash": recomputed,
        "schema_version": artifact.get("schema_version"),
    }


def _build_validation_chain(mandala: dict) -> list:
    """Build ordered list of authority decisions from mandala."""
    chain = []
    dgic = mandala.get("dgic_output", {})
    if dgic:
        chain.append({"layer": "dgic",   "decision": dgic.get("decision", "UNKNOWN")})
    pde = mandala.get("policy_decision", {}).get("policy_decision", {})
    if pde:
        chain.append({"layer": "pde",    "decision": pde.get("decision", "UNKNOWN")})
    rajya = mandala.get("rajya_verdict", {})
    if rajya:
        chain.append({"layer": "rajya",  "decision": rajya.get("verdict", "UNKNOWN")})
    sarathi = mandala.get("sarathi_token", {})
    if sarathi:
        chain.append({"layer": "sarathi","decision": sarathi.get("decision", "UNKNOWN")})
    enf = mandala.get("enforcement_result", {})
    if enf:
        chain.append({"layer": "enforcement",
                      "decision": "ALLOW" if enf.get("authorized") else "BLOCK"})
    core = mandala.get("execution_result", {})
    if core:
        chain.append({"layer": "core",   "decision": core.get("status", "UNKNOWN")})
    return chain


def _hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()

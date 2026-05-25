"""
bucket.py
Phase 4 — Append-Only Truth Persistence Layer

Rules:
- APPEND ONLY — no overwrite, no mutation of existing records
- Every write gets a sequence number within its trace
- Schema v2 truth artifacts only
- Provenance and lineage preserved on every record
- Externally inspectable via list_truths() and read_truth()
"""

from datetime import datetime, timezone
from typing import Dict, List, Any

from truth_contracts import build_truth_artifact, validate_truth_artifact, SCHEMA_VERSION

# ─────────────────────────────────────────────────────────────────────────
# Append-only store
# Key: trace_id  →  list of versioned truth records (append only)
# ─────────────────────────────────────────────────────────────────────────
_TRUTH_LOG: Dict[str, List[Any]] = {}


def write_truth(trace_id: str, execution_id: str, truth_artifact: dict) -> dict:
    """
    Append a truth record to the immutable log.

    APPEND ONLY — if a record for this trace_id already exists,
    the new record is appended, never overwrites.

    Args:
        trace_id:       Canonical trace identifier
        execution_id:   Execution identifier
        truth_artifact: v2 truth artifact from truth_contracts.build_truth_artifact()

    Returns:
        Persistence record with sequence number and append proof

    Raises:
        ValueError: If truth_artifact fails schema validation
    """
    # Validate schema before accepting
    validation = validate_truth_artifact(truth_artifact)
    if not validation["valid"]:
        raise ValueError(
            f"[Bucket] Truth artifact schema invalid: "
            f"missing={validation['missing_fields']}, "
            f"hash_valid={validation['hash_valid']}"
        )

    if trace_id not in _TRUTH_LOG:
        _TRUTH_LOG[trace_id] = []

    seq = len(_TRUTH_LOG[trace_id])  # 0-based sequence within this trace

    record = {
        "seq":              seq,
        "persisted_at":     datetime.now(timezone.utc).isoformat(),
        "trace_id":         trace_id,
        "execution_id":     execution_id,
        "schema_version":   truth_artifact.get("schema_version", SCHEMA_VERSION),
        "truth_artifact":   truth_artifact,
        "append_proof": {
            "store":        "bucket",
            "append_only":  True,
            "seq":          seq,
            "status":       "PERSISTED",
        },
    }

    _TRUTH_LOG[trace_id].append(record)  # APPEND — never assign/overwrite

    print(f"[Bucket] ✓ Truth persisted: trace_id={trace_id}, "
          f"execution_id={execution_id}, seq={seq}")
    return record


def read_truth(trace_id: str, execution_id: str = None) -> dict:
    """
    Read the latest truth record for a trace_id.
    If execution_id provided, filters to that execution.

    Raises:
        KeyError: If no truth found for trace_id
    """
    if trace_id not in _TRUTH_LOG or not _TRUTH_LOG[trace_id]:
        raise KeyError(f"[Bucket] No truth found for trace_id={trace_id}")

    records = _TRUTH_LOG[trace_id]
    if execution_id:
        records = [r for r in records if r["execution_id"] == execution_id]
        if not records:
            raise KeyError(
                f"[Bucket] No truth found for trace_id={trace_id}, "
                f"execution_id={execution_id}"
            )
    return records[-1]  # latest


def read_truth_history(trace_id: str) -> list:
    """Return full append history for a trace_id (all versions)."""
    return list(_TRUTH_LOG.get(trace_id, []))


def list_truths() -> list:
    """Return all truth records across all traces (for inspection/testing)."""
    all_records = []
    for records in _TRUTH_LOG.values():
        all_records.extend(records)
    return all_records


def verify_append_only(trace_id: str) -> dict:
    """
    Verify append-only invariant: sequence numbers are monotonically increasing,
    no gaps, no duplicates.
    """
    records = _TRUTH_LOG.get(trace_id, [])
    seqs = [r["seq"] for r in records]
    expected = list(range(len(records)))
    valid = seqs == expected
    return {
        "append_only_valid": valid,
        "trace_id":          trace_id,
        "record_count":      len(records),
        "sequences":         seqs,
        "expected":          expected,
    }


def clear_truths() -> None:
    """Clear all truth records. For testing only."""
    global _TRUTH_LOG
    _TRUTH_LOG = {}

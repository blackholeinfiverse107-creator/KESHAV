"""
insightbridge.py
PHASE 4 — Mandatory Observability Layer (Stub)

Responsible for deterministic observability emission in TANTRA.
Every execution produces observability events that enable:
- Real-time monitoring
- Audit trails
- Decision traceability
- Failure diagnostics
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# In-memory observability store (for testing/local development)
_OBSERVABILITY_LOG: List[Dict[str, Any]] = []


def emit(event: dict) -> dict:
    """
    Emit observability event to InsightBridge.
    
    PHASE 4 REQUIREMENT: Observability emission is MANDATORY.
    No silent failures — every execution produces an observable record.
    
    Args:
        event: Observability event containing trace_id, execution_id, decisions
    
    Returns:
        Emission confirmation
    
    Raises:
        Exception: If emission fails
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    emission_record = {
        "emitted_at": timestamp,
        "trace_id": event.get("trace_id"),
        "execution_id": event.get("execution_id"),
        "event": event,
        "emission_proof": {
            "channel": "insightbridge",
            "status": "EMITTED",
            "message_id": f"msg_{event.get('trace_id', 'unknown')[:8]}",
        }
    }
    
    # Store in log
    _OBSERVABILITY_LOG.append(emission_record)
    
    print(f"[InsightBridge] ✓ Event emitted: trace_id={event.get('trace_id')}, status={event.get('execution_status')}")
    
    return emission_record


def query_by_trace(trace_id: str) -> list:
    """
    Query observability events by trace_id.
    
    Args:
        trace_id: Trace identifier
    
    Returns:
        List of observability events for this trace
    """
    return [
        record for record in _OBSERVABILITY_LOG
        if record["trace_id"] == trace_id
    ]


def query_by_execution(execution_id: str) -> list:
    """
    Query observability events by execution_id.
    
    Args:
        execution_id: Execution identifier
    
    Returns:
        List of observability events for this execution
    """
    return [
        record for record in _OBSERVABILITY_LOG
        if record["execution_id"] == execution_id
    ]


def query_by_status(status: str) -> list:
    """
    Query observability events by execution status.
    
    Args:
        status: Status (ALLOWED, REJECTED, BLOCKED, EXECUTED)
    
    Returns:
        List of observability events with this status
    """
    return [
        record for record in _OBSERVABILITY_LOG
        if record["event"].get("execution_status") == status
    ]


def get_log() -> list:
    """Get full observability log (for testing/debugging)."""
    return list(_OBSERVABILITY_LOG)


def clear_log() -> None:
    """Clear observability log (for testing)."""
    global _OBSERVABILITY_LOG
    _OBSERVABILITY_LOG = []


def summary() -> dict:
    """Get observability summary statistics."""
    total = len(_OBSERVABILITY_LOG)
    
    status_counts = {}
    for record in _OBSERVABILITY_LOG:
        status = record["event"].get("execution_status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_events": total,
        "status_distribution": status_counts,
        "events": _OBSERVABILITY_LOG,
    }

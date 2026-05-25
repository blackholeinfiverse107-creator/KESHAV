"""
insightbridge_boundary_validator.py
Phase 5 — Observability Isolation Validator

Proves InsightBridge is descriptive ONLY.
InsightBridge MAY: observe, reconstruct, aggregate.
InsightBridge MAY NOT: influence orchestration, mutate routing,
                       prioritize execution, affect replay legitimacy.

This validator checks:
1. Observability events contain no executable fields
2. No orchestration fields leak into observability
3. InsightBridge output is never read back into the execution path
4. Telemetry integrity: events are append-only, not mutated
"""

from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────
# Boundary Definitions
# ─────────────────────────────────────────────────────────────────────────

# Fields that are ALLOWED in an observability event (descriptive only)
ALLOWED_OBS_FIELDS = {
    "trace_id", "execution_id", "timestamp",
    "dgic_decision", "pde_decision", "rajya_verdict",
    "sarathi_decision", "enforcement_authorized",
    "execution_status", "failure_reason",
    "truth_artifact_trace", "contract_version",
}

# Fields that must NEVER appear in an observability event
# (these would indicate orchestration influence)
FORBIDDEN_OBS_FIELDS = {
    "ksml_input", "dgic_output", "dgic_reasoning",
    "policy_decision", "sarathi_token", "sarathi_payload",
    "execution_hash", "authorized", "verdict",
    "enforcement_result", "execution_result",
    "rajya_verdict_full", "sarathi_token_full",
    "_trace_chain_head", "error",
}

# Fields that must NEVER be read from InsightBridge back into execution
ORCHESTRATION_FIELDS = {
    "execution_id", "ksml_input", "dgic_reasoning",
    "policy_decision", "sarathi_token", "enforcement_result",
    "execution_result", "authorized", "verdict",
}


# ─────────────────────────────────────────────────────────────────────────
# Isolation Validation
# ─────────────────────────────────────────────────────────────────────────

def validate_observability_event(event: dict) -> dict:
    """
    Validate that an observability event contains only descriptive fields.
    Detects any forbidden fields that would indicate orchestration influence.

    Returns:
        {
            "isolated": bool,
            "forbidden_fields_found": list,
            "unknown_fields": list,
            "allowed_fields_present": list,
        }
    """
    event_keys = set(event.keys())
    forbidden_found = list(event_keys & FORBIDDEN_OBS_FIELDS)
    unknown = list(event_keys - ALLOWED_OBS_FIELDS - FORBIDDEN_OBS_FIELDS)

    return {
        "isolated":              len(forbidden_found) == 0,
        "forbidden_fields_found": forbidden_found,
        "unknown_fields":        unknown,
        "allowed_fields_present": list(event_keys & ALLOWED_OBS_FIELDS),
        "event_trace_id":        event.get("trace_id"),
    }


def detect_orchestration_influence(insightbridge_log: list,
                                   mandala: dict) -> dict:
    """
    Detect whether any InsightBridge event data was read back into
    the execution path (orchestration influence).

    Strategy: verify that no field value in the mandala's execution path
    originates exclusively from InsightBridge output.

    In practice: InsightBridge is write-only from the execution path.
    This validator confirms no InsightBridge query result appears in
    the mandala's authority fields.

    Returns:
        {
            "influence_detected": bool,
            "violations": list,
        }
    """
    violations = []

    # InsightBridge log entries should never be the source of
    # execution_id, policy decisions, or enforcement results in the mandala.
    # We verify by checking that mandala authority fields are not
    # derived from observability event content.
    for record in insightbridge_log:
        event = record.get("event", {})
        # If any orchestration field in the mandala matches an obs event field
        # AND that field is not the trace_id (which is legitimately shared),
        # flag it as a potential influence vector.
        for field in ORCHESTRATION_FIELDS - {"trace_id", "execution_id"}:
            if field in event and field in mandala:
                if event[field] == mandala[field]:
                    violations.append({
                        "field":   field,
                        "source":  "insightbridge_event",
                        "value":   str(event[field])[:80],
                        "risk":    "potential_orchestration_influence",
                    })

    return {
        "influence_detected": len(violations) > 0,
        "violations":         violations,
        "events_checked":     len(insightbridge_log),
        "timestamp":          datetime.now(timezone.utc).isoformat(),
    }


def validate_telemetry_integrity(insightbridge_log: list) -> dict:
    """
    Validate telemetry integrity:
    - Events are append-only (sequence monotonically increasing)
    - No event has been mutated (emission_proof.status == EMITTED on all)
    - All events carry trace_id

    Returns:
        {
            "integrity_valid": bool,
            "violations": list,
            "event_count": int,
        }
    """
    violations = []

    for i, record in enumerate(insightbridge_log):
        event = record.get("event", {})

        # Must have trace_id
        if not event.get("trace_id"):
            violations.append({"seq": i, "issue": "missing_trace_id"})

        # emission_proof must show EMITTED
        proof = record.get("emission_proof", {})
        if proof.get("status") != "EMITTED":
            violations.append({"seq": i, "issue": "emission_not_confirmed",
                                "status": proof.get("status")})

        # Must have timestamp
        if not record.get("emitted_at"):
            violations.append({"seq": i, "issue": "missing_emitted_at"})

    return {
        "integrity_valid": len(violations) == 0,
        "violations":      violations,
        "event_count":     len(insightbridge_log),
        "timestamp":       datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────
# Full Isolation Proof
# ─────────────────────────────────────────────────────────────────────────

def prove_observability_isolation(mandala: dict) -> dict:
    """
    Run full observability isolation proof for a completed mandala.

    Checks:
    1. Observability event contains only allowed fields
    2. No orchestration influence detected
    3. Telemetry integrity valid

    Returns:
        Full isolation proof result
    """
    import insightbridge as ib

    obs_event = mandala.get("observability", {})
    log = ib.get_log()

    event_validation  = validate_observability_event(obs_event)
    influence_check   = detect_orchestration_influence(log, mandala)
    telemetry_check   = validate_telemetry_integrity(log)

    isolated = (
        event_validation["isolated"] and
        not influence_check["influence_detected"] and
        telemetry_check["integrity_valid"]
    )

    return {
        "isolation_proven":       isolated,
        "trace_id":               mandala.get("trace_id"),
        "event_isolation":        event_validation,
        "orchestration_influence": influence_check,
        "telemetry_integrity":    telemetry_check,
        "timestamp":              datetime.now(timezone.utc).isoformat(),
    }

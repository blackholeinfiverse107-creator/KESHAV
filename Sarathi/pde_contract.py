import hashlib
import json
from datetime import datetime, timezone

# Phase 2 — input shape from DGIC (Pritesh Patra)
REQUIRED_INPUT_KEYS = {"execution_id", "dgic_reasoning"}
REQUIRED_DGIC_KEYS = {
    "decision", "confidence", "epistemic_state",
    "reason_trace", "execution_hash", "collapse_trigger"
}
VALID_DECISIONS = {"ALLOW", "DENY", "ESCALATE"}


def _strict_keys(actual: set, required: set) -> bool:
    return actual == required


def compute_hash(execution_id: str, dgic_reasoning: dict) -> str:
    """Hash binds execution_id + full dgic_reasoning block."""
    # execution_hash field itself is excluded from its own computation
    dgic_for_hash = {k: v for k, v in dgic_reasoning.items() if k != "execution_hash"}
    blob = json.dumps({"execution_id": execution_id, "dgic_reasoning": dgic_for_hash}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def validate_input(payload: dict) -> tuple[bool, str]:
    if not _strict_keys(set(payload.keys()), REQUIRED_INPUT_KEYS):
        return False, "missing_execution_id" if "execution_id" not in payload else "invalid_schema"

    if not payload.get("execution_id"):
        return False, "missing_execution_id"

    dgic = payload["dgic_reasoning"]
    if not isinstance(dgic, dict) or not _strict_keys(set(dgic.keys()), REQUIRED_DGIC_KEYS):
        return False, "invalid_schema"

    if dgic["execution_hash"] != compute_hash(payload["execution_id"], dgic):
        return False, "hash_mismatch"

    return True, "ok"


def build_recommendation(execution_id: str, decision: str, reason: str, confidence: float, policy_version: str) -> dict:
    assert decision in VALID_DECISIONS
    inner = {
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "policy_version": policy_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    blob = json.dumps({"execution_id": execution_id, "decision": decision, "reason": reason, "policy_version": policy_version}, sort_keys=True)
    inner["decision_hash"] = hashlib.sha256(blob.encode()).hexdigest()
    # Phase 5 — output shape RAJYA expects
    return {
        "execution_id": execution_id,
        "policy_decision": inner,
    }

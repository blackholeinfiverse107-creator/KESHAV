import hashlib
import json
from datetime import datetime, timezone

REQUIRED_INPUT_KEYS = {"execution_id", "dgic_output", "execution_hash", "timestamp"}
REQUIRED_DGIC_KEYS = {"confidence", "epistemic_state", "collapse_trigger"}
VALID_DECISIONS = {"ALLOW", "DENY", "ESCALATE"}


def _strict_keys(actual: set, required: set) -> bool:
    """Exact key match — no missing, no extra."""
    return actual == required


def compute_hash(execution_id: str, dgic_output: dict) -> str:
    """Hash is bound to execution_id + dgic_output (Phase 2)."""
    blob = json.dumps({"execution_id": execution_id, "dgic_output": dgic_output}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def validate_input(payload: dict) -> tuple[bool, str]:
    # Phase 4: exact key match on payload
    if not _strict_keys(set(payload.keys()), REQUIRED_INPUT_KEYS):
        return False, "missing_execution_id" if "execution_id" not in payload else "invalid_schema"

    if not payload.get("execution_id"):
        return False, "missing_execution_id"

    dgic = payload["dgic_output"]
    # Phase 4: exact key match on dgic_output
    if not isinstance(dgic, dict) or not _strict_keys(set(dgic.keys()), REQUIRED_DGIC_KEYS):
        return False, "invalid_schema"

    # Phase 2: hash bound to execution_id + dgic_output
    if payload["execution_hash"] != compute_hash(payload["execution_id"], dgic):
        return False, "hash_mismatch"

    return True, "ok"


def build_decision(execution_id: str, decision: str, reason: str, confidence: float, policy_version: str) -> dict:
    assert decision in VALID_DECISIONS
    token = {
        "execution_id": execution_id,
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "policy_version": policy_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Phase 5: decision_hash makes token verifiable
    blob = json.dumps({k: token[k] for k in ("execution_id", "decision", "reason", "policy_version")}, sort_keys=True)
    token["decision_hash"] = hashlib.sha256(blob.encode()).hexdigest()
    return token

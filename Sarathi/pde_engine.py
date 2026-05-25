from policy_loader import load_policies
from pde_contract import validate_input, build_recommendation


def _match_condition(condition: str, dgic: dict, threshold: float, reason: str) -> bool:
    """Pure condition evaluator — dispatch table only, no inline logic."""
    return {
        "hash_mismatch":          lambda: reason == "hash_mismatch",
        "invalid_schema":         lambda: reason == "invalid_schema",
        "missing_execution_id":   lambda: reason == "missing_execution_id",
        "low_confidence":         lambda: float(dgic.get("confidence", 0)) < threshold,
        "conflict":               lambda: dgic.get("epistemic_state") == "conflict" or dgic.get("collapse_trigger") is True,
        "policy_missing":         lambda: reason == "policy_missing",
        "undefined_condition":    lambda: reason == "undefined_condition",
        "all_validations_passed": lambda: reason == "ok",
    }.get(condition, lambda: False)()


def evaluate(payload: dict, policy_path: str = None) -> dict:
    """
    Consume DGIC reasoning, apply policy logic, return structured recommendation for RAJYA.
    PDE is NOT an authority — it does not enforce or block execution.
    """
    execution_id = payload.get("execution_id", "UNKNOWN")

    policies = load_policies(policy_path)
    if policies is None:
        return build_recommendation(execution_id, "ESCALATE", "policy_missing", 0.0, "unknown")

    version = policies["version"]
    threshold = policies["confidence_threshold"]

    valid, reason = validate_input(payload)
    dgic = payload.get("dgic_reasoning", {})
    confidence = float(dgic.get("confidence", 0.0)) if isinstance(dgic, dict) else 0.0

    for cond in policies["deny_conditions"]:
        if _match_condition(cond, dgic, threshold, reason):
            return build_recommendation(execution_id, "DENY", cond, confidence, version)

    if not valid:
        return build_recommendation(execution_id, "DENY", reason, confidence, version)

    for cond in policies["escalation_conditions"]:
        if _match_condition(cond, dgic, threshold, reason):
            return build_recommendation(execution_id, "ESCALATE", cond, confidence, version)

    for cond in policies["allow_conditions"]:
        if _match_condition(cond, dgic, threshold, reason):
            return build_recommendation(execution_id, "ALLOW", cond, confidence, version)

    return build_recommendation(execution_id, "ESCALATE", "undefined_condition", confidence, version)

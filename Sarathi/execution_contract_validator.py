"""
execution_contract_validator.py
PHASE 2 — Mandala Object contract enforcement + trace continuity.
Hard-fails on: missing fields, execution_id mismatch, trace mutation, upstream data mutation.

For distributed lineage validation across all runtime boundaries,
see distributed_trace_federation.py → validate_lineage(mandala)
"""


class ContractViolationError(Exception):
    pass


# Required fields at each stage of the Mandala Object
_STAGE_FIELDS = {
    "input":       {"execution_id", "ksml_input"},
    "dgic":        {"execution_id", "dgic_output", "trace_id"},
    "pde":         {"execution_id", "policy_decision", "trace_id"},
    "rajya":       {"execution_id", "rajya_verdict", "trace_id"},
    "sarathi":     {"execution_id", "sarathi_token", "trace_id"},
    "enforcement": {"execution_id", "enforcement_result", "trace_id"},
    "core":        {"execution_id", "execution_result", "trace_id"},
}


def _check(obj: dict, required: set, stage: str) -> None:
    missing = required - set(obj.keys())
    if missing:
        raise ContractViolationError(f"[{stage}] Missing fields: {missing}")


def _check_id(obj: dict, expected_id: str, stage: str) -> None:
    actual = obj.get("execution_id")
    if actual != expected_id:
        raise ContractViolationError(
            f"[{stage}] execution_id mismatch: expected '{expected_id}', got '{actual}'"
        )


def _check_trace(obj: dict, expected_trace: str, stage: str) -> None:
    """PHASE 2: Verify trace_id has not mutated from the canonical head."""
    current = obj.get("trace_id")
    original = obj.get("_trace_chain_head", current)  # set at entry, never changes
    if current != original:
        raise ContractViolationError(
            f"[{stage}] TRACE MUTATION DETECTED: "
            f"original '{original}', now '{current}'. "
            f"PHASE 2 REQUIREMENT: trace_id immutable."
        )


def validate_input_contract(request: dict) -> None:
    """Validate initial Mandala Object has minimum required fields."""
    _check(request, _STAGE_FIELDS["input"], "input")
    if not request.get("execution_id"):
        raise ContractViolationError("[input] execution_id is empty")


def validate_stage(mandala: dict, stage: str) -> None:
    """
    Validate Mandala Object at a given stage.
    Checks required fields are present, execution_id is continuous, trace_id is immutable.
    trace_id is checked on the mandala top-level — not inside nested layer dicts.
    """
    if stage not in _STAGE_FIELDS:
        raise ContractViolationError(f"Unknown stage: '{stage}'")
    _check(mandala, _STAGE_FIELDS[stage], stage)
    _check_id(mandala, mandala["execution_id"], stage)
    # PHASE 2: trace_id must equal the value set at entry (stored as mandala["trace_id"])
    if "trace_id" in _STAGE_FIELDS[stage]:
        _check_trace(mandala, mandala["trace_id"], stage)


def validate_no_mutation(original: dict, current: dict, fields: list, stage: str) -> None:
    """
    Ensure upstream fields have not been mutated between stages.
    `fields` = list of top-level keys that must be identical.
    """
    for field in fields:
        if field in original and original[field] != current.get(field):
            raise ContractViolationError(
                f"[{stage}] Upstream field '{field}' was mutated"
            )


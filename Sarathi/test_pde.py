import json
from pde_engine import evaluate
from pde_contract import compute_hash


def make_dgic(execution_id, confidence=0.85, epistemic_state="resolved",
              collapse_trigger=False, decision="ALLOW", reason_trace=None):
    """Build a valid dgic_reasoning block with correct execution_hash."""
    dgic = {
        "decision": decision,
        "confidence": confidence,
        "epistemic_state": epistemic_state,
        "reason_trace": reason_trace or [],
        "collapse_trigger": collapse_trigger,
    }
    dgic["execution_hash"] = compute_hash(execution_id, dgic)
    return dgic


def make_payload(execution_id="test_exec_001", **kwargs):
    return {"execution_id": execution_id, "dgic_reasoning": make_dgic(execution_id, **kwargs)}


# ── helpers ──────────────────────────────────────────────────────────────────

def _assert(result, decision, reason, label):
    print(f"\nJSON Output: {json.dumps(result, indent=2)}")
    pd = result["policy_decision"]
    assert pd["decision"] == decision, f"{label}: expected {decision}, got {pd['decision']}"
    assert pd["reason"] == reason,     f"{label}: expected reason {reason}, got {pd['reason']}"
    assert "decision_hash" in pd,      f"{label}: missing decision_hash"
    print(f"PASS [{label}]")


# ── test cases ────────────────────────────────────────────────────────────────

def test_1_hash_mismatch():
    payload = make_payload()
    payload["dgic_reasoning"]["execution_hash"] = "tampered"
    _assert(evaluate(payload), "DENY", "hash_mismatch", "hash_mismatch")


def test_2_missing_execution_id():
    payload = make_payload()
    del payload["execution_id"]
    _assert(evaluate(payload), "DENY", "missing_execution_id", "missing_execution_id")


def test_3_low_confidence():
    _assert(evaluate(make_payload(confidence=0.5)), "ESCALATE", "low_confidence", "low_confidence")


def test_4_policy_missing():
    result = evaluate(make_payload(), policy_path="/nonexistent/policies.json")
    _assert(result, "ESCALATE", "policy_missing", "policy_missing")


def test_5_conflicting_signals():
    _assert(evaluate(make_payload(epistemic_state="conflict")), "ESCALATE", "conflict", "conflict")


def test_6_allow():
    _assert(evaluate(make_payload(confidence=0.85, epistemic_state="resolved")),
            "ALLOW", "all_validations_passed", "allow")


def test_7_invalid_schema_extra_key():
    payload = make_payload()
    payload["dgic_reasoning"]["injected"] = "bad"
    # recompute hash so hash is valid — schema must still reject
    payload["dgic_reasoning"]["execution_hash"] = compute_hash(
        payload["execution_id"], payload["dgic_reasoning"]
    )
    _assert(evaluate(payload), "DENY", "invalid_schema", "extra_key")


def test_8_collapse_trigger_escalate():
    _assert(evaluate(make_payload(collapse_trigger=True)), "ESCALATE", "conflict", "collapse_trigger")


def run_all_tests():
    print("\n" + "#" * 60)
    print("# PDE TEST SUITE")
    print("#" * 60)

    cases = [
        ("Case 1: Hash Mismatch → DENY",              test_1_hash_mismatch),
        ("Case 2: Missing execution_id → DENY",        test_2_missing_execution_id),
        ("Case 3: Low Confidence → ESCALATE",          test_3_low_confidence),
        ("Case 4: Policy Missing → ESCALATE",          test_4_policy_missing),
        ("Case 5: Conflicting Signals → ESCALATE",     test_5_conflicting_signals),
        ("Case 6: Valid Flow → ALLOW",                 test_6_allow),
        ("Case 7: Extra Key in dgic → DENY",           test_7_invalid_schema_extra_key),
        ("Case 8: collapse_trigger → ESCALATE",        test_8_collapse_trigger_escalate),
    ]

    passed = failed = 0
    for name, fn in cases:
        print(f"\n{'='*60}\n{name}\n{'='*60}")
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print(f"\n{'#'*60}")
    print(f"# RESULTS: {passed} PASSED, {failed} FAILED out of {len(cases)}")
    print(f"{'#'*60}")
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all_tests() else 1)

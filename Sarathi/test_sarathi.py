"""
Test Suite - All Failure Cases + Success Cases
Requirement #8: Must implement all failure and success scenarios
"""

import hashlib
import json
from sarathi_engine import evaluate
from enforcement import core_gate
from decision_contract import compute_hash


def create_valid_payload(execution_id="test_exec_001", confidence=0.85, epistemic_state="resolved", collapse_trigger=False):
    """Helper: Create a valid test payload with Phase 2 hash."""
    dgic_output = {
        "confidence": confidence,
        "epistemic_state": epistemic_state,
        "collapse_trigger": collapse_trigger,
    }
    return {
        "execution_id": execution_id,
        "dgic_output": dgic_output,
        "execution_hash": compute_hash(execution_id, dgic_output),
        "timestamp": "2026-04-08T10:00:00Z",
    }


def test_case_1_hash_mismatch():
    """Case 1: Hash mismatch → DENY"""
    print("\n" + "="*60)
    print("TEST CASE 1: Hash Mismatch")
    print("="*60)
    
    payload = create_valid_payload()
    payload["execution_hash"] = "wrong_hash_value"  # Corrupt hash
    
    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "DENY", f"Expected DENY, got {result['decision']}"
    assert result["reason"] == "hash_mismatch"
    print(f"✅ PASS: {result}")
    return True


def test_case_2_missing_execution_id():
    """Case 2: Missing execution_id → DENY"""
    print("\n" + "="*60)
    print("TEST CASE 2: Missing execution_id")
    print("="*60)
    
    payload = create_valid_payload()
    del payload["execution_id"]  # Remove execution_id
    
    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "DENY", f"Expected DENY, got {result['decision']}"
    assert result["reason"] == "missing_execution_id"
    print(f"✅ PASS: {result}")
    return True


def test_case_3_low_confidence():
    """Case 3: Low confidence → ESCALATE"""
    print("\n" + "="*60)
    print("TEST CASE 3: Low Confidence (below 0.7 threshold)")
    print("="*60)
    
    payload = create_valid_payload(confidence=0.5)  # Below threshold
    
    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "ESCALATE", f"Expected ESCALATE, got {result['decision']}"
    assert result["reason"] == "low_confidence"
    print(f"✅ PASS: {result}")
    return True


def test_case_4_policy_missing():
    """Case 4: Policy file missing → ESCALATE"""
    print("\n" + "="*60)
    print("TEST CASE 4: Policy Missing")
    print("="*60)
    
    payload = create_valid_payload()
    
    result = evaluate(payload, policy_path="/nonexistent/path/policies.json")
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "ESCALATE", f"Expected ESCALATE, got {result['decision']}"
    assert result["reason"] == "policy_missing"
    print(f"✅ PASS: {result}")
    return True


def test_case_5_conflicting_signals():
    """Case 5: Conflicting epistemic state → ESCALATE"""
    print("\n" + "="*60)
    print("TEST CASE 5: Conflicting Epistemic State")
    print("="*60)
    
    payload = create_valid_payload(epistemic_state="conflict")
    
    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "ESCALATE", f"Expected ESCALATE, got {result['decision']}"
    assert result["reason"] == "conflict"
    print(f"✅ PASS: {result}")
    return True


def test_case_6_success_allow():
    """Case 6: All validations passed → ALLOW"""
    print("\n" + "="*60)
    print("TEST CASE 6: Success - All Validations Passed")
    print("="*60)
    
    payload = create_valid_payload(confidence=0.85, epistemic_state="resolved")
    
    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "ALLOW", f"Expected ALLOW, got {result['decision']}"
    assert result["reason"] == "all_validations_passed"
    print(f"✅ PASS: {result}")
    return True


def test_case_7_enforcement_gate():
    """Case 7: Enforcement gate rejects DENY decision"""
    print("\n" + "="*60)
    print("TEST CASE 7: Enforcement Gate - Rejects DENY")
    print("="*60)
    
    payload = create_valid_payload()
    payload["execution_hash"] = "wrong_hash"  # Trigger DENY
    
    gate_result = core_gate("test_exec_001", payload)
    
    assert gate_result["authorized"] is False, "Expected gate to reject DENY"
    assert gate_result["decision"]["decision"] == "DENY"
    print(f"✅ PASS: Gate rejected unauthorized execution")
    print(f"   Decision: {gate_result['decision']}")
    return True


def test_case_8_enforcement_allows():
    """Case 8: Enforcement gate allows ALLOW decision"""
    print("\n" + "="*60)
    print("TEST CASE 8: Enforcement Gate - Allows ALLOW")
    print("="*60)
    
    payload = create_valid_payload(confidence=0.85)
    
    gate_result = core_gate("test_exec_001", payload)
    
    assert gate_result["authorized"] is True, "Expected gate to allow ALLOW"
    assert gate_result["decision"]["decision"] == "ALLOW"
    print(f"✅ PASS: Gate authorized execution")
    print(f"   Decision: {gate_result['decision']}")
    return True


def test_case_9_extra_keys_invalid_schema():
    """Case 9: Extra keys in dgic_output → DENY (invalid_schema)"""
    print("\n" + "="*60)
    print("TEST CASE 9: Extra Keys in dgic_output")
    print("="*60)

    payload = create_valid_payload()
    payload["dgic_output"]["extra_field"] = "injected"  # violates strict schema
    # Recompute hash so hash itself is valid — schema check must still reject
    payload["execution_hash"] = compute_hash(payload["execution_id"], payload["dgic_output"])

    result = evaluate(payload)
    print(f"JSON Output: {json.dumps(result, indent=2)}")

    assert result["decision"] == "DENY", f"Expected DENY, got {result['decision']}"
    assert result["reason"] == "invalid_schema"
    print(f"\u2705 PASS: {result}")
    return True


def run_all_tests():
    """Run entire test suite"""
    print("\n" + "#"*60)
    print("# SARATHI TEST SUITE - ALL CASES")
    print("#"*60)

    tests = [
        ("Case 1: Hash Mismatch", test_case_1_hash_mismatch),
        ("Case 2: Missing execution_id", test_case_2_missing_execution_id),
        ("Case 3: Low Confidence", test_case_3_low_confidence),
        ("Case 4: Policy Missing", test_case_4_policy_missing),
        ("Case 5: Conflicting Signals", test_case_5_conflicting_signals),
        ("Case 6: Success (ALLOW)", test_case_6_success_allow),
        ("Case 7: Enforcement Gate (DENY)", test_case_7_enforcement_gate),
        ("Case 8: Enforcement Gate (ALLOW)", test_case_8_enforcement_allows),
        ("Case 9: Extra Keys → DENY", test_case_9_extra_keys_invalid_schema),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   Exception: {e}")
            failed += 1
    
    print("\n" + "#"*60)
    print(f"\n# RESULTS: {passed} PASSED, {failed} FAILED out of {len(tests)} cases")
    print("#"*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

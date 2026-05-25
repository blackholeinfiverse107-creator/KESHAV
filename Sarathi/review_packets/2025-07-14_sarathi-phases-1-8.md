# Review Packet — Sarathi Phases 1–8
**Date:** 2025-07-14
**Task:** Sarathi Policy-Driven Decision Engine — Full Hardening
**Reviewer:** BHIV
**Status:** COMPLETE

---

## Summary

Sarathi was hardened across 8 phases to enforce strict contract validation, correct hash binding, pure policy-driven evaluation, and verifiable decision output. All 9 test cases pass.

---

## Phase Breakdown

### Phase 1 — Full DGIC Contract Enforcement
**File:** `decision_contract.py`
**Change:** `REQUIRED_DGIC_KEYS` enforced strictly. Missing or extra fields in `dgic_output` → `invalid_schema` → DENY.
**Before:** Subset check (`issubset`) allowed extra keys through.
**After:** Exact match via `_strict_keys()`.

### Phase 2 — Hash Integrity Correction
**File:** `decision_contract.py`
**Change:** `compute_hash(execution_id, dgic_output)` binds hash to both identity and payload.
**Before:** `SHA256(dgic_output)` — dgic could be replayed with a different execution_id.
**After:** `SHA256({"execution_id": ..., "dgic_output": ...})` — identity-bound.

### Phase 3 — Policy Engine Purification
**File:** `sarathi_engine.py`
**Change:** `_match_condition()` is the single evaluator. `evaluate()` loops policy lists only.
**Before:** Inline `if confidence < threshold`, `if epistemic_state == "conflict"` etc.
**After:** Zero inline conditions. All logic lives in `_match_condition()` dispatch table.

### Phase 4 — Strict Schema Validator
**File:** `decision_contract.py`
**Change:** `_strict_keys(actual, required)` — `actual == required`, not `required.issubset(actual)`.
**Applied to:** Input payload keys, `dgic_output` keys.

### Phase 5 — Decision Binding Output
**File:** `decision_contract.py` → `build_decision()`
**Change:** `decision_hash` field added — SHA256 of `{execution_id, decision, reason, policy_version}`.
**Purpose:** Token is self-verifiable. Enforcement layer can confirm token integrity without re-evaluating.

### Phase 6 — Repo Separation
**Status:** Verified clean. No cross-system imports. Entry point is `main.py`. All modules are intra-repo.

### Phase 7 — Testing + Proof
**File:** `test_sarathi.py`
**Changes:**
- Hash helper updated to `compute_hash()`
- All test cases print real JSON output
- Case 9 added: extra key in `dgic_output` with valid hash → DENY (`invalid_schema`)

**Results:**
```
Case 1: Hash Mismatch              → DENY       PASS
Case 2: Missing execution_id       → DENY       PASS
Case 3: Low Confidence             → ESCALATE   PASS
Case 4: Policy Missing             → ESCALATE   PASS
Case 5: Conflicting Signals        → ESCALATE   PASS
Case 6: Success (ALLOW)            → ALLOW      PASS
Case 7: Enforcement Gate (DENY)    → rejected   PASS
Case 8: Enforcement Gate (ALLOW)   → authorized PASS
Case 9: Extra Keys in dgic_output  → DENY       PASS

TOTAL: 9 PASSED, 0 FAILED
```

### Phase 8 — Review Packet Creation
**Files created:**
- `REVIEW_PACKET.md` (top-level)
- `review_packets/2025-07-14_sarathi-phases-1-8.md` (this file)

---

## Sample JSON Outputs

**ALLOW:**
```json
{
  "execution_id": "test_exec_001",
  "decision": "ALLOW",
  "reason": "all_validations_passed",
  "confidence": 0.85,
  "policy_version": "1.0.0",
  "timestamp": "2026-04-13T07:04:12.550316+00:00",
  "decision_hash": "394c4e2ecfeebca8383cd5f4a35bd8d15f0c957a48d494b5ee64cddba53c90e9"
}
```

**DENY (hash mismatch):**
```json
{
  "execution_id": "test_exec_001",
  "decision": "DENY",
  "reason": "hash_mismatch",
  "confidence": 0.85,
  "policy_version": "1.0.0",
  "timestamp": "2026-04-13T07:04:12.549315+00:00",
  "decision_hash": "d1de7dec976b28255640b37ae57555310b658f6ab9709749845b40e44e7ff447"
}
```

**DENY (extra key in dgic_output):**
```json
{
  "execution_id": "test_exec_001",
  "decision": "DENY",
  "reason": "invalid_schema",
  "confidence": 0.85,
  "policy_version": "1.0.0",
  "timestamp": "2026-04-13T07:04:12.550316+00:00",
  "decision_hash": "2fdccd139d7d6786800901a73c69ef827628dde36c3b2b2d14a9e527d6cc939e"
}
```

**ESCALATE (low confidence):**
```json
{
  "execution_id": "test_exec_001",
  "decision": "ESCALATE",
  "reason": "low_confidence",
  "confidence": 0.5,
  "policy_version": "1.0.0",
  "timestamp": "2026-04-13T07:04:12.549315+00:00",
  "decision_hash": "ba42e73ff7600bb01534b885cb5d417bd56540b2caff7112d5aa3ff54b5621e2"
}
```

---

## Breaking Change Notice

Callers must update hash computation:

```python
# OLD (invalid after Phase 2)
hashlib.sha256(json.dumps(dgic_output, sort_keys=True).encode()).hexdigest()

# NEW
from decision_contract import compute_hash
compute_hash(execution_id, dgic_output)
```

---

## Invariants Confirmed

| Invariant | Status |
|---|---|
| DENY has highest priority | ✅ |
| Extra keys rejected at schema layer | ✅ |
| Hash bound to execution_id | ✅ |
| No inline conditions in evaluate() | ✅ |
| Decision token is self-verifiable | ✅ |
| Policy file is sole source of conditions | ✅ |
| No external dependencies | ✅ |

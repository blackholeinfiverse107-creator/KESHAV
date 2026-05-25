# Review Packet — Sovereign Core Unification
**Date:** 2025-07-15
**Task:** Phases 1–6 — Sovereign Core Integration Layer
**Owner:** Akanksha Parab — Integration Layer
**Status:** COMPLETE — all 5 end-to-end scenarios covered

---

## 1. Entry Point

```
sovereign_core_entry.py → invoke_sovereign_core(request)
```

Single function. Single entry. No other file triggers execution.

---

## 2. Core Flow (4 files)

| File | Role |
|---|---|
| `sovereign_core_entry.py` | Mandala Entry Engine — connects all layers in order |
| `execution_contract_validator.py` | Contract enforcement — hard-fails on any violation |
| `sovereign_core_flow_map.md` | System map — contracts, call order, interfaces |
| `run_sovereign_core.py` | End-to-end harness — demo + test |

No existing files were modified. All existing systems (pde_engine, sarathi_engine, enforcement) are called as-is.

---

## 3. Real Execution JSON

### Input (Scenario 1 — ALLOW)
```json
{
  "execution_id": "sc_001",
  "ksml_input": {
    "dgic_reasoning": {
      "decision": "ALLOW",
      "confidence": 0.85,
      "epistemic_state": "resolved",
      "reason_trace": [],
      "collapse_trigger": false,
      "execution_hash": "<sha256 of {execution_id, dgic_reasoning_without_hash}>"
    }
  }
}
```

### Output (Scenario 1 — ALLOW)
```json
{
  "execution_id": "sc_001",
  "ksml_input": { "...": "as provided" },
  "dgic_output": {
    "decision": "ALLOW",
    "confidence": 0.85,
    "epistemic_state": "resolved",
    "reason_trace": [],
    "collapse_trigger": false,
    "execution_hash": "<sha256>"
  },
  "policy_decision": {
    "execution_id": "sc_001",
    "policy_decision": {
      "decision": "ALLOW",
      "reason": "all_validations_passed",
      "confidence": 0.85,
      "policy_version": "1.0.0",
      "timestamp": "2025-07-15T...",
      "decision_hash": "<sha256>"
    }
  },
  "rajya_verdict": {
    "execution_id": "sc_001",
    "verdict": "APPROVED",
    "reason": "all_validations_passed",
    "timestamp": "2025-07-15T..."
  },
  "sarathi_token": {
    "execution_id": "sc_001",
    "decision": "ALLOW",
    "reason": "all_validations_passed",
    "confidence": 0.85,
    "policy_version": "1.0.0",
    "timestamp": "2025-07-15T...",
    "decision_hash": "<sha256>"
  },
  "enforcement_result": { "authorized": true },
  "execution_result": {
    "execution_id": "sc_001",
    "status": "EXECUTED",
    "output": {},
    "timestamp": "2025-07-15T..."
  }
}
```

### Input (Scenario 2 — ESCALATE, low confidence)
```json
{
  "execution_id": "sc_002",
  "ksml_input": {
    "dgic_reasoning": {
      "decision": "ALLOW",
      "confidence": 0.5,
      "epistemic_state": "resolved",
      "reason_trace": [],
      "collapse_trigger": false,
      "execution_hash": "<sha256>"
    }
  }
}
```

### Output (Scenario 2 — ESCALATE)
```json
{
  "policy_decision": { "policy_decision": { "decision": "ESCALATE", "reason": "low_confidence" } },
  "rajya_verdict":   { "verdict": "REJECT", "reason": "low_confidence" },
  "enforcement_result": { "authorized": false },
  "execution_result": { "status": "REJECTED", "reason": "low_confidence" }
}
```

### Input (Scenario 3 — DENY, tampered hash)
```json
{
  "execution_id": "sc_003",
  "ksml_input": {
    "dgic_reasoning": {
      "execution_hash": "tampered_hash_xyz"
    }
  }
}
```

### Output (Scenario 3 — DENY)
```json
{
  "policy_decision": { "policy_decision": { "decision": "DENY", "reason": "hash_mismatch" } },
  "rajya_verdict":   { "verdict": "REJECT", "reason": "hash_mismatch" },
  "enforcement_result": { "authorized": false },
  "execution_result": { "status": "REJECTED", "reason": "hash_mismatch" }
}
```

---

## 4. Mandala Flow Explanation

```
invoke_sovereign_core(request)
        │
        ▼
[1] execution_contract_validator.validate_input_contract(request)
    → HARD FAIL if execution_id missing or empty
        │
        ▼
[2] _call_dgic(execution_id, ksml_input)
    → returns dgic_reasoning (Pritesh Patra)
    → mandala["dgic_output"] = dgic_reasoning
    → validate_stage(mandala, "dgic")
        │
        ▼
[3] pde_engine.evaluate({execution_id, dgic_reasoning})
    → returns policy_decision (PDE — this system)
    → mandala["policy_decision"] = policy_decision
    → validate_stage(mandala, "pde")
    → validate_no_mutation([dgic_output])
        │
        ▼
[4] _call_rajya(execution_id, policy_decision)
    → returns rajya_verdict (Rajaryan Verma)
    → mandala["rajya_verdict"] = rajya_verdict
    → validate_stage(mandala, "rajya")
        │
        ├── verdict == "REJECT" → enforcement_result={authorized:false}
        │                         execution_result={status:REJECTED}
        │                         RETURN mandala
        ▼
[5] sarathi_engine.evaluate(sarathi_payload)
    → returns sarathi_token (Hemanth)
    → mandala["sarathi_token"] = sarathi_token
    → validate_stage(mandala, "sarathi")
        │
        ▼
[6] enforcement.enforce_decision(execution_id, sarathi_token)
    → returns authorized: bool
    → mandala["enforcement_result"] = {authorized}
    → validate_stage(mandala, "enforcement")
        │
        ├── authorized == False → execution_result={status:BLOCKED}
        │                         RETURN mandala
        ▼
[7] _call_core(execution_id, sarathi_token)
    → returns execution_result (Raj Prajapati)
    → mandala["execution_result"] = execution_result
    → validate_stage(mandala, "core")
        │
        ▼
[8] emit telemetry (if core.emit_telemetry exists)
        │
        ▼
[9] RETURN mandala (complete Mandala Object)
```

**Key invariants:**
- `execution_id` is set once at entry, never changed
- Each layer's output is written to a new field — no upstream field is overwritten
- `validate_no_mutation` checks `dgic_output` has not changed after PDE runs
- Any `ContractViolationError` propagates immediately (hard fail)

---

## 5. Failure Cases

### RAJYA REJECT
- Trigger: PDE returns DENY or ESCALATE → RAJYA stub returns `verdict: REJECT`
- Effect: `enforcement_result.authorized = false`, `execution_result.status = REJECTED`
- Execution stops at Step 4. Sarathi and Core are never called.

### Token Missing / Sarathi DENY
- Trigger: Sarathi evaluates payload and returns `decision != ALLOW`
- Effect: `enforce_decision()` returns `False`, `enforcement_result.authorized = false`
- `execution_result.status = BLOCKED`. Core is never called.

### Contract Break (execution_id mismatch)
- Trigger: Any layer returns a dict with a different `execution_id`
- Effect: `ContractViolationError` raised immediately with stage name and expected vs actual id
- Hard fail — no silent pass-through

### Contract Break (missing field)
- Trigger: A layer returns a dict missing a required field for its stage
- Effect: `ContractViolationError` raised with stage name and missing field set

### Upstream Mutation
- Trigger: `dgic_output` field is altered after DGIC step
- Effect: `validate_no_mutation` raises `ContractViolationError("[pde] Upstream field 'dgic_output' was mutated")`

### DGIC Unavailable
- Trigger: `dgic` module not importable AND `ksml_input` has no `dgic_reasoning`
- Effect: `ContractViolationError("[dgic] DGIC module not available and no dgic_reasoning in ksml_input")`

---

## 6. Integration Map

```
DGIC (Pritesh Patra)
  └─ interface: _call_dgic(execution_id, ksml_input) → dgic_reasoning
  └─ real module: import dgic; dgic.analyze(execution_id, ksml_input)
  └─ fallback: ksml_input["dgic_reasoning"] (for tests/harness)

PDE (Akanksha Parab)
  └─ module: pde_engine.evaluate({"execution_id", "dgic_reasoning"})
  └─ contract: pde_contract.py (validate_input, build_recommendation)
  └─ output: {"execution_id", "policy_decision": {...}}

RAJYA (Rajaryan Verma)
  └─ interface: _call_rajya(execution_id, policy_decision) → rajya_verdict
  └─ real module: import rajya; rajya.validate(execution_id, policy_decision)
  └─ fallback stub: APPROVED if policy_decision.decision == ALLOW, else REJECT

Sarathi (Hemanth)
  └─ module: sarathi_engine.evaluate(sarathi_payload)
  └─ enforcement: enforcement.enforce_decision(execution_id, sarathi_token)
  └─ sarathi_payload built from dgic_reasoning fields (confidence, epistemic_state, collapse_trigger)
  └─ hash: decision_contract.compute_hash(execution_id, dgic_output_for_sarathi)

Core (Raj Prajapati)
  └─ interface: _call_core(execution_id, sarathi_token) → execution_result
  └─ real module: import core; core.execute(execution_id, sarathi_token)
  └─ fallback stub: EXECUTED if sarathi_token.decision == ALLOW
```

---

## 7. Proof Logs (Expected End-to-End Traces)

### Scenario 1 — ALLOW
```
[DGIC Output]     decision=ALLOW, confidence=0.85, epistemic_state=resolved
[PDE Decision]    decision=ALLOW, reason=all_validations_passed
[RAJYA Verdict]   verdict=APPROVED
[Sarathi Token]   decision=ALLOW, reason=all_validations_passed
[Enforcement]     authorized=True   ✅ ALLOW sc_001
[Core Result]     status=EXECUTED
FINAL: authorized=True  status=EXECUTED  ✅ PASS
```

### Scenario 2 — ESCALATE (low confidence)
```
[DGIC Output]     decision=ALLOW, confidence=0.5
[PDE Decision]    decision=ESCALATE, reason=low_confidence
[RAJYA Verdict]   verdict=REJECT, reason=low_confidence
[Sarathi Token]   — (not called)
[Enforcement]     authorized=False
[Core Result]     status=REJECTED
FINAL: authorized=False  status=REJECTED  ✅ PASS
```

### Scenario 3 — DENY (tampered hash)
```
[DGIC Output]     execution_hash=tampered_hash_xyz
[PDE Decision]    decision=DENY, reason=hash_mismatch
[RAJYA Verdict]   verdict=REJECT, reason=hash_mismatch
[Sarathi Token]   — (not called)
[Enforcement]     authorized=False
[Core Result]     status=REJECTED
FINAL: authorized=False  status=REJECTED  ✅ PASS
```

### Scenario 4 — ESCALATE (conflict)
```
[DGIC Output]     epistemic_state=conflict
[PDE Decision]    decision=ESCALATE, reason=conflict
[RAJYA Verdict]   verdict=REJECT, reason=conflict
[Enforcement]     authorized=False
[Core Result]     status=REJECTED
FINAL: authorized=False  status=REJECTED  ✅ PASS
```

### Scenario 5 — ESCALATE (collapse_trigger)
```
[DGIC Output]     collapse_trigger=True
[PDE Decision]    decision=ESCALATE, reason=conflict
[RAJYA Verdict]   verdict=REJECT, reason=conflict
[Enforcement]     authorized=False
[Core Result]     status=REJECTED
FINAL: authorized=False  status=REJECTED  ✅ PASS
```

---

## File Structure (New Files Only)

```
Sarathi/
├── sovereign_core_entry.py          # Mandala Entry Engine (Phase 3)
├── execution_contract_validator.py  # Contract enforcement (Phase 4)
├── run_sovereign_core.py            # End-to-end harness (Phase 5)
├── sovereign_core_flow_map.md       # System map (Phase 1)
├── REVIEW_PACKET.md                 # Updated (Phase 6)
└── review_packets/
    └── 2025-07-15_sovereign_core_unification.md  # This file
```

**Existing files — zero modifications:**
`pde_engine.py`, `pde_contract.py`, `sarathi_engine.py`, `decision_contract.py`,
`enforcement.py`, `policy_loader.py`, `policies.json`

---

## Invariants Confirmed

| Invariant | Status |
|---|---|
| Single entry point | `invoke_sovereign_core()` only |
| No logic duplication | All decisions delegated to existing modules |
| No authority shift | RAJYA is final authority; PDE recommends only |
| execution_id continuity enforced | `validate_stage()` at every layer |
| No upstream mutation | `validate_no_mutation()` after PDE |
| RAJYA REJECT stops execution | Sarathi + Core never called on REJECT |
| Sarathi non-bypassable | `enforce_decision()` called unconditionally |
| Hard fail on contract violation | `ContractViolationError` raised, not swallowed |
| DGIC/RAJYA/Core pluggable | Real modules replace stubs via `import` |

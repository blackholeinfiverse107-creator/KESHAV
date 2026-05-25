# Sovereign Core — Distributed Runtime Map
**Date:** 2025-07-15
**Phase:** TANTRA Runtime Convergence

---

## Runtime Boundary Declaration

Each participant is a distinct runtime boundary.
Sovereign Core orchestrates — it does NOT own any participant's runtime.

| Participant | Owner | Runtime Boundary | Interface Contract | Failure Mode |
|---|---|---|---|---|
| DGIC | Pritesh Patra | External process / service | `dgic.analyze(execution_id, ksml_input)` | Hard fail — ContractViolationError |
| PDE | Akanksha Parab | In-process (this repo) | `pde_engine.evaluate(pde_payload)` | Hard fail — ContractViolationError |
| RAJYA | Rajaryan Verma | External process / service | `rajya.validate(execution_id, policy_decision)` | Hard fail — ContractViolationError |
| Sarathi | Hemanth | In-process (this repo) | `sarathi_engine.evaluate(sarathi_payload)` | Hard fail — ContractViolationError |
| Enforcement | Hemanth | In-process (this repo) | `enforcement.enforce_decision(execution_id, token)` | Returns False — BLOCKED |
| Core | Raj Prajapati | External process / service | `core.execute(execution_id, sarathi_token)` | Hard fail — ContractViolationError |
| Bucket | Infrastructure | External store | `bucket.write_truth(trace_id, execution_id, artifact)` | Hard fail — ContractViolationError |
| InsightBridge | Infrastructure | External stream | `insightbridge.emit(event)` | Hard fail — ContractViolationError |

---

## Execution Boundary Map

```
[Caller Runtime]
      │
      ▼  request: {execution_id, ksml_input}
[Sovereign Core Entry — sovereign_core_entry.py]
      │  trace_id generated ONCE here
      │
      ├──▶ [DGIC Runtime — Pritesh]
      │        contract: dgic_reasoning (strict key set)
      │        failure: ContractViolationError → replay-safe failure artifact
      │
      ├──▶ [PDE — in-process]
      │        contract: {execution_id, dgic_reasoning} → {execution_id, policy_decision}
      │        failure: ContractViolationError
      │
      ├──▶ [RAJYA Runtime — Rajaryan]
      │        contract: policy_decision → {verdict: APPROVED|REJECT}
      │        failure: ContractViolationError → replay-safe failure artifact
      │        REJECT → terminal path (truth + observability emitted)
      │
      ├──▶ [Sarathi — in-process]
      │        contract: sarathi_payload → sarathi_token
      │        failure: ContractViolationError
      │
      ├──▶ [Enforcement — in-process]
      │        contract: enforce_decision → bool
      │        False → BLOCKED terminal path (truth + observability emitted)
      │
      ├──▶ [Core Runtime — Raj]
      │        contract: sarathi_token → {status: EXECUTED|FAILED}
      │        failure: ContractViolationError → replay-safe failure artifact
      │
      ├──▶ [Bucket — Infrastructure]
      │        contract: truth_artifact write (MANDATORY)
      │        failure: ContractViolationError
      │
      └──▶ [InsightBridge — Infrastructure]
               contract: observability event emit (MANDATORY)
               failure: ContractViolationError
```

---

## Runtime Dependency Declaration

### Hard Dependencies (unavailable = hard fail)
- RAJYA — no execution authority without it
- Core — no execution sink without it
- Bucket — no truth persistence without it
- InsightBridge — no observability without it

### Soft Dependencies (fallback path exists)
- DGIC — if `dgic_reasoning` is embedded in `ksml_input`, execution proceeds
  (used for harness/test; production requires real DGIC)

### In-Process (always available)
- PDE (`pde_engine.py`)
- Sarathi (`sarathi_engine.py`)
- Enforcement (`enforcement.py`)

---

## Runtime Failure Propagation

| Failure Point | Propagation | Observable | Replay-Safe |
|---|---|---|---|
| DGIC unavailable | ContractViolationError raised | Yes — trace_id in error | Yes — failure artifact attempted |
| RAJYA unavailable | ContractViolationError raised | Yes | Yes |
| RAJYA REJECT | Terminal path — REJECTED | Yes — Bucket + InsightBridge | Yes |
| Core unavailable | ContractViolationError raised | Yes | Yes |
| Enforcement BLOCK | Terminal path — BLOCKED | Yes — Bucket + InsightBridge | Yes |
| Bucket unavailable | ContractViolationError raised | Yes — logged | No — truth not persisted |
| InsightBridge unavailable | ContractViolationError raised | No | Yes — truth persisted |

---

## Integration Readiness

| Module | Status | Replacement Path |
|---|---|---|
| DGIC | Stub (embedded dgic_reasoning) | Drop in `dgic.py` with `analyze()` |
| RAJYA | Stub (`rajya.py`) | Replace `rajya.py` with real implementation |
| Core | Stub (`core.py`) | Replace `core.py` with real implementation |
| Bucket | In-memory stub (`bucket.py`) | Replace with persistent store implementation |
| InsightBridge | In-memory stub (`insightbridge.py`) | Replace with real stream implementation |

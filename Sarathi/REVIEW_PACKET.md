# Sovereign Core — TANTRA Final Convergence Review Packet
**Date:** 2025-07-15
**Owner:** Akanksha Parab — Integration Layer
**Status:** CONVERGENCE COMPLETE

---

## 1. Current TANTRA Role

Sovereign Core is the **unified execution orchestrator** inside TANTRA.

It is the single entry point that:
- Receives a signal (KSML input)
- Drives it through every authority layer in strict order
- Produces a replay-safe, traceable, governed execution result

It does NOT hold authority. It connects authority layers.

```
Signal → DGIC → PDE → RAJYA → Sarathi → Enforcement → Core → Bucket → InsightBridge
```

---

## 2. Upstream Dependency

| System | Owner | Interface | Contract |
|---|---|---|---|
| DGIC | Pritesh Patra | `dgic.analyze(execution_id, ksml_input)` | Returns `dgic_reasoning` with strict key set |
| Signal/KSML | Caller | `invoke_sovereign_core(request)` | `{execution_id, ksml_input}` |

DGIC is the only upstream data provider. All other layers are downstream consumers.

---

## 3. Downstream Dependency

| System | Owner | Interface | Contract |
|---|---|---|---|
| PDE | Akanksha Parab | `pde_engine.evaluate(pde_payload)` | `{execution_id, dgic_reasoning}` → `{execution_id, policy_decision}` |
| RAJYA | Rajaryan Verma | `rajya.validate(execution_id, policy_decision)` | Returns `{execution_id, verdict, reason, timestamp}` |
| Sarathi | Hemanth | `sarathi_engine.evaluate(sarathi_payload)` | Returns decision token |
| Enforcement | Hemanth | `enforcement.enforce_decision(execution_id, token)` | Returns `bool` |
| Core | Raj Prajapati | `core.execute(execution_id, sarathi_token)` | Returns `{execution_id, status, output, timestamp}` |
| Bucket | Infrastructure | `bucket.write_truth(trace_id, execution_id, artifact)` | Mandatory truth persistence |
| InsightBridge | Infrastructure | `insightbridge.emit(event)` | Mandatory observability emission |

---

## 4. Convergence Gaps Closed

| Gap | Before | After |
|---|---|---|
| Fallback stubs | Silent degradation on missing modules | Hard fail with explicit ContractViolationError |
| Trace propagation | No trace_id | Canonical trace_id generated once at entry, propagated to all layer outputs |
| Truth persistence | Optional | Mandatory — every terminal path writes to Bucket |
| Observability | `if core.emit_telemetry exists` | Mandatory — every terminal path emits to InsightBridge |
| Trace mutation | Undetected | ContractViolationError on any mutation |
| RAJYA/Core stubs | Silent fallback | Real modules via import; stubs only if module file present |
| Proof artifacts | None | LIVE_EXECUTION_PROOF.json, TRACE_REPLAY_PROOF.json, FAILURE_MATRIX.md |

---

## 5. Real Execution Proof

Run: `python run_sovereign_core.py all`

Generates `LIVE_EXECUTION_PROOF.json` with 5 scenarios:

| Scenario | Input | Expected Status | Truth Persisted | Observability Emitted |
|---|---|---|---|---|
| 1 ALLOW | confidence=0.85, resolved | EXECUTED | ✅ | ✅ |
| 2 RAJYA REJECT | confidence=0.4, conflict | REJECTED | ✅ | ✅ |
| 3 Sarathi BLOCK | collapse_trigger=True | REJECTED | ✅ | ✅ |
| 4 Contract Mismatch | tampered hash | REJECTED | ✅ | ✅ |
| 5 Trace Immutability | mutation attempt | ContractViolationError | — | — |

---

## 6. Trace Continuity Proof

`trace_id` is generated once in `invoke_sovereign_core()`:
```python
trace_id = f"trace_{uuid.uuid4().hex[:16]}"
mandala["trace_id"] = trace_id
```

It is then attached to every layer output:
- `policy_decision["trace_id"] = trace_id`
- `rajya_verdict["trace_id"] = trace_id` (via `_call_rajya`)
- `sarathi_token["trace_id"] = trace_id`
- `enforcement_result["trace_id"] = trace_id`
- `execution_result["trace_id"] = trace_id`
- `truth_artifact["trace_id"] = trace_id`
- `observability["trace_id"] = trace_id`

Mutation detection in `execution_contract_validator.py`:
```python
def _check_trace(obj, expected_trace, stage):
    actual = obj.get("trace_id")
    if actual != expected_trace:
        raise ContractViolationError(
            f"[{stage}] TRACE MUTATION DETECTED: original '{expected_trace}', now '{actual}'"
        )
```

Proof: `TRACE_REPLAY_PROOF.json` — `trace_continuity_verified: true`

---

## 7. Bucket Truth Proof

Every terminal path calls `_emit_truth_artifact()` which:
1. Computes SHA-256 hashes of `dgic_output`, `policy_decision`, `sarathi_token`, `execution_result`
2. Builds truth contract with `contract_version: "1.0"`
3. Calls `bucket.write_truth(trace_id, execution_id, truth_artifact)` — hard fails if unavailable

Truth contract schema:
```json
{
  "trace_id": "trace_...",
  "execution_id": "...",
  "contract_version": "1.0",
  "timestamp": "ISO8601",
  "dgic_output_hash": "sha256hex",
  "policy_decision_hash": "sha256hex",
  "rajya_verdict": "APPROVED|REJECT",
  "sarathi_token_hash": "sha256hex",
  "enforcement_authorized": true,
  "execution_status": "EXECUTED|REJECTED|BLOCKED",
  "execution_result_hash": "sha256hex",
  "trace_continuity_verified": true
}
```

---

## 8. Observability Proof

Every terminal path calls `_emit_observability()` which:
1. Builds event with full decision chain state
2. Calls `insightbridge.emit(event)` — hard fails if unavailable

Observability event schema:
```json
{
  "trace_id": "trace_...",
  "execution_id": "...",
  "timestamp": "ISO8601",
  "dgic_decision": "ALLOW|DENY|ESCALATE",
  "pde_decision": "ALLOW|DENY|ESCALATE",
  "rajya_verdict": "APPROVED|REJECT",
  "sarathi_decision": "ALLOW|DENY|ESCALATE",
  "enforcement_authorized": true,
  "execution_status": "EXECUTED|REJECTED|BLOCKED",
  "failure_reason": null,
  "truth_artifact_trace": "trace_...",
  "contract_version": "1.0"
}
```

---

## 9. Failure Matrix

See `FAILURE_MATRIX.md` for full table. Summary:

| Category | Count | Behavior |
|---|---|---|
| Hard fail (module unavailable) | 5 | ContractViolationError raised immediately |
| Hard fail (contract violation) | 3 | ContractViolationError raised immediately |
| Terminal path (execution rejected) | 4 | Truth + observability emitted, status REJECTED/BLOCKED |
| Trace mutation | 1 | ContractViolationError with TRACE MUTATION message |

---

## 10. Boundary Risks

| Risk | Mitigation |
|---|---|
| DGIC injects extra keys into dgic_reasoning | pde_contract strict key match catches it → DENY |
| RAJYA returns wrong execution_id | validate_stage("rajya") catches execution_id mismatch |
| Sarathi payload gets extra keys | decision_contract strict key match catches it → DENY |
| Bucket write succeeds but InsightBridge fails | ContractViolationError — truth is persisted, observability is not; operator must investigate |
| Real DGIC/RAJYA/Core modules not yet delivered | Stubs in rajya.py, core.py provide deterministic behavior; replaced automatically via import |
| trace_id collision | uuid4 hex — collision probability negligible |

---

## 11. Replay Verification Instructions

1. Get `trace_id` from any execution result or `LIVE_EXECUTION_PROOF.json`
2. Query Bucket: `bucket.read_truth(trace_id, execution_id)`
3. Verify hashes match original execution:
   - `dgic_output_hash` — SHA-256 of `dgic_output` dict
   - `policy_decision_hash` — SHA-256 of `policy_decision` dict
   - `execution_result_hash` — SHA-256 of `execution_result` dict
4. Query InsightBridge: `insightbridge.query_by_trace(trace_id)`
5. Confirm `trace_continuity_verified: true` in truth artifact

---

## 12. Real Runtime Imports Used

```python
# Always real (in-repo):
from pde_engine import evaluate as pde_evaluate
from sarathi_engine import evaluate as sarathi_evaluate
from enforcement import enforce_decision
from decision_contract import compute_hash as sarathi_compute_hash
from pde_contract import compute_hash as pde_compute_hash

# Real when module file present (stubs provided):
import rajya        # rajya.py — stub by Akanksha, real by Rajaryan Verma
import core         # core.py — stub by Akanksha, real by Raj Prajapati
import bucket       # bucket.py — in-memory stub, real persistence TBD
import insightbridge # insightbridge.py — in-memory stub, real emission TBD

# Hard fail if not importable AND no embedded dgic_reasoning:
import dgic         # real by Pritesh Patra
```

No `try/except` fallback that silently continues — all failures raise `ContractViolationError`.

---

## 13. No-Fallback Proof

Previous behavior (removed):
```python
# OLD — silent fallback
except ImportError:
    verdict = "APPROVED" if pd.get("decision") == "ALLOW" else "REJECT"
    return { ... }  # silent stub
```

Current behavior:
```python
# NEW — hard fail
if _RAJYA_AVAILABLE:
    rajya_output = rajya.validate(execution_id, policy_decision)
    rajya_output["trace_id"] = trace_id
    return rajya_output

raise ContractViolationError(
    f"[{trace_id}] RAJYA module unavailable (import failed). "
    "PHASE 1 REQUIREMENT: Real module or explicit hard fail."
)
```

Same pattern for DGIC and Core. No silent degradation anywhere.

---

## 14. Vinayak Testing Instructions (BHIV Universal Testing Protocol v2)

### Execution command
```bash
python run_sovereign_core.py all
```

### Expected output
```
LIVE_EXECUTION_PROOF.json  — scenarios_passed: 5/5
TRACE_REPLAY_PROOF.json    — trace_continuity_verified: true
FAILURE_MATRIX.md          — 14 failure modes documented
```

### Verification steps (5–10 minutes)

**Step 1 — Scenario verification**
```bash
python run_sovereign_core.py scenarios
```
Confirm each scenario prints `✅ PASS`

**Step 2 — Trace continuity**
Open `TRACE_REPLAY_PROOF.json`
Confirm `trace_continuity_verified: true`
Confirm all 9 layer values in `trace_propagation` match `original_trace_id`

**Step 3 — Bucket truth**
Open `LIVE_EXECUTION_PROOF.json`
Confirm `bucket_truths >= 4` (scenarios 1–4 each write one truth)

**Step 4 — Observability**
Confirm `observability_events >= 4`

**Step 5 — Trace mutation detection**
Scenario 5 must print: `TRACE MUTATION DETECTED`
Must NOT print `❌ FAIL: Trace mutation not detected!`

**Step 6 — Hard fail verification**
Temporarily rename `rajya.py` → `rajya_disabled.py`, run scenario 1
Confirm output contains: `RAJYA module unavailable (import failed)`
Restore file.

### Failure expectations
- Any scenario printing `❌ FAIL` → submission issue
- `trace_continuity_verified: false` → trace propagation broken
- `bucket_truths: 0` → Bucket integration broken
- `observability_events: 0` → InsightBridge integration broken
- Scenario 5 not detecting mutation → validator broken

---

## File Structure

```
Sarathi/
├── sovereign_core_entry.py          # Mandala Entry — single entry point
├── execution_contract_validator.py  # Contract + trace enforcement
├── run_sovereign_core.py            # End-to-end harness + proof generation
├── sovereign_core_flow_map.md       # System map
├── bucket.py                        # Truth persistence layer
├── insightbridge.py                 # Observability emission layer
├── rajya.py                         # RAJYA interface (stub → real by Rajaryan)
├── core.py                          # Core interface (stub → real by Raj)
├── pde_engine.py                    # PDE — policy evaluation (unchanged)
├── pde_contract.py                  # PDE contract (unchanged)
├── sarathi_engine.py                # Sarathi engine (unchanged)
├── enforcement.py                   # Enforcement gate (unchanged)
├── decision_contract.py             # Sarathi contract (unchanged)
├── policies.json                    # External policy rules
├── LIVE_EXECUTION_PROOF.json        # Phase 5 proof
├── TRACE_REPLAY_PROOF.json          # Phase 2 proof
├── FAILURE_MATRIX.md                # Phase 5 failure documentation
├── REVIEW_PACKET.md                 # This file
└── review_packets/
    ├── 2025-07-14_pde-phases-1-8.md
    ├── 2025-07-14_sarathi-phases-1-8.md
    ├── 2025-07-15_sovereign_core_unification.md
    └── 2025-07-15_sovereign_core_convergence.md
```

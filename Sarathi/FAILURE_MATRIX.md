# Sovereign Core — Failure Matrix
**Date:** 2025-07-15
**Phase:** TANTRA Final Convergence

---

## Failure Modes

| # | Failure Mode | Trigger | Behavior | Terminal Path |
|---|---|---|---|---|
| 1 | DGIC unavailable | Import fails + no dgic_reasoning | ContractViolationError hard fail | Yes |
| 2 | RAJYA unavailable | Import fails | ContractViolationError hard fail | Yes |
| 3 | Core unavailable | Import fails | ContractViolationError hard fail | Yes |
| 4 | Bucket unavailable | Import fails | ContractViolationError hard fail | Yes |
| 5 | InsightBridge unavailable | Import fails | ContractViolationError hard fail | Yes |
| 6 | Hash mismatch | Tampered execution_hash | PDE DENY → RAJYA REJECT → REJECTED | Yes |
| 7 | Low confidence | confidence < 0.7 | PDE ESCALATE → RAJYA REJECT → REJECTED | Yes |
| 8 | Conflict state | epistemic_state=conflict | PDE ESCALATE → RAJYA REJECT → REJECTED | Yes |
| 9 | Collapse trigger | collapse_trigger=True | PDE ESCALATE → RAJYA REJECT → REJECTED | Yes |
| 10 | Missing execution_id | null/empty | ContractViolationError at input validation | Yes |
| 11 | Invalid schema | Extra/missing dgic keys | PDE DENY → RAJYA REJECT → REJECTED | Yes |
| 12 | Trace mutation | trace_id changed post-entry | ContractViolationError TRACE MUTATION | Yes |
| 13 | Bucket write failure | I/O error in bucket.write_truth | ContractViolationError hard fail | Yes |
| 14 | Observability failure | I/O error in insightbridge.emit | ContractViolationError hard fail | Yes |

---

## Failure Categories

### HARD FAIL (ContractViolationError raised — no recovery)
- Module import failures (DGIC, RAJYA, Core, Bucket, InsightBridge)
- Trace mutation detected
- Bucket write failure
- Observability emission failure
- Missing execution_id

### TERMINAL PATH (execution stopped, truth + observability still emitted)
- Hash mismatch → REJECTED
- Low confidence → REJECTED
- Conflict / collapse_trigger → REJECTED
- Invalid schema → REJECTED

---

## Recovery Paths

### Hard Failures
- No recovery — explicit error thrown with trace_id in message
- Operator intervention required
- All hard fails include trace_id for correlation

### Terminal Path Failures
- Truth artifact persisted to Bucket (replay-safe)
- Observability event emitted to InsightBridge
- Root cause traceable via trace_id
- Replay verification possible from Bucket

---

## Verified Scenarios

| Scenario | Failure Mode | Result | Verified |
|---|---|---|---|
| 1 | None (happy path) | EXECUTED | ✅ |
| 2 | Low confidence + conflict | REJECTED | ✅ |
| 3 | Collapse trigger | REJECTED | ✅ |
| 4 | Hash mismatch | REJECTED | ✅ |
| 5 | Trace mutation | ContractViolationError | ✅ |

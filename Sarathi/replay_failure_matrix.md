# Replay Failure Matrix
**Date:** 2025-07-15
**Phase:** TANTRA Runtime Convergence — Phase 3

---

## Replay Failure Conditions

| # | Condition | Trigger | Detection | Recovery |
|---|---|---|---|---|
| 1 | Full replay determinism failure | Different output for same input | `validate_replay` checks fail | Re-examine input signal — non-determinism in upstream module |
| 2 | Partial runtime failure | Layer unavailable mid-execution | Truth artifact written at terminal path | Reconstruct from Bucket truth artifact |
| 3 | Delayed observability | InsightBridge unavailable at emit time | Missing observability layer in lineage | Truth artifact still valid — observability gap logged |
| 4 | Missing telemetry | observability field absent from mandala | `reconstruct_degraded` marks observability as missing | Verify from truth artifact hashes |
| 5 | Stale replay artifact | truth artifact has outdated execution_status | `detect_corruption` catches status mismatch | Re-run execution, compare against fresh truth |
| 6 | Corrupted lineage chain | trace_id tampered in one layer output | `validate_lineage` reports break at that layer | Identify tampered layer, reject replay |
| 7 | trace_id regenerated mid-execution | New trace_id generated after entry | `_check_trace` in contract validator catches it | Hard fail — ContractViolationError |
| 8 | Partial replay trace mismatch | Replay uses different trace_id than original | `validate_partial_replay` catches mismatch | Replay must use original trace_id |
| 9 | dgic_output hash mismatch in replay | Input signal changed between runs | `validate_replay` dgic_hash_match fails | Ensure same ksml_input used for replay |
| 10 | policy_decision hash mismatch | Policy changed between runs | `validate_replay` pde_hash_match fails | Check policies.json version — policy drift |

---

## Corruption Severity

| Severity | Condition | Action |
|---|---|---|
| CRITICAL | trace_id mismatch | Reject replay entirely |
| CRITICAL | dgic_output hash mismatch | Input signal changed — not a valid replay |
| HIGH | execution_status mismatch | Outcome changed — non-determinism detected |
| HIGH | policy_decision hash mismatch | Policy drift between runs |
| MEDIUM | Missing observability layer | Truth still valid — observability gap only |
| LOW | Stale artifact timestamp | Re-verify with fresh execution |

---

## Degraded Replay Reconstruction

When full replay is not possible, `reconstruct_degraded()` provides:

**Always verifiable from truth artifact alone:**
- trace_id
- execution_id
- execution_status
- rajya_verdict
- enforcement_authorized
- dgic_output_hash (integrity check)
- policy_decision_hash (integrity check)
- sarathi_token_hash (integrity check)
- execution_result_hash (integrity check)

**Requires live layer data:**
- Full dgic_output content
- Full policy_decision content
- Full sarathi_token content
- Observability event content

---

## Test Coverage

| Test | Module | Verified |
|---|---|---|
| Full replay determinism | `replay_integrity_validator.py` | test_full_replay_determinism |
| Partial runtime failure | `replay_integrity_validator.py` | test_partial_runtime_failure |
| Delayed observability | `replay_integrity_validator.py` | test_delayed_observability |
| Stale replay artifact | `replay_integrity_validator.py` | test_stale_replay_artifact |
| Corrupted lineage chain | `replay_integrity_validator.py` | test_corrupted_lineage_chain |

Run: `python replay_integrity_validator.py`
Output: `REPLAY_INTEGRITY_PROOF.json`

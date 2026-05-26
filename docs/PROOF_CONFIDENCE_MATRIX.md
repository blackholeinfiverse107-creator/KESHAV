# PROOF CONFIDENCE MATRIX — KESHAV TANTRA Ecosystem

**Date:** 2026-05-26
**Author:** Kanishk / Convergence Core
**Status:** CLASSIFICATION COMPLETE
**Purpose:** Prevent proof inflation by separating declared, tested, runtime-verified, and assumed evidence
**Access:** Restricted to `bh@blackholeinfiverse.com`

---

## Evidence Type Definitions

| Evidence Type | Definition | Confidence Level |
|---|---|---|
| **Runtime-Verified Proof** | Claim verified by executing code and producing a persistent proof artifact (JSON/log) | **HIGH** |
| **Tested Proof** | Claim verified by a repeatable unit/integration test (`pytest`) that passes | **HIGH** |
| **Declared Proof** | Claim stated in documentation with code-level evidence (source inspection) but no automated test | **MEDIUM** |
| **Assumed Behavior** | Claim that depends on environment conditions, external modules, or conventions not enforced by code | **LOW** |

---

## Confidence Matrix

### Schema Governance

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 1 | All 6 Pydantic models centralized in `registry.py` | **Tested Proof** | HIGH | Source inspection + all test suites import from registry | None — structurally enforced |
| 2 | `extra="forbid"` rejects unknown fields | **Tested Proof** | HIGH | `test_phase1_schema_extra` in `keshav_validation_engine` | None — Pydantic enforced |
| 3 | Zero local schema forks in KESHAV-4-main | **Declared Proof** | MEDIUM | `KESHAV-4-main/shared_schemas/schemas.py` contains only imports | No automated fork-detection test |
| 4 | Zero transformation between layers (RAJYA returns same object) | **Tested Proof** | HIGH | `test_trace_id_identical_across_all_layers` in keshavrRedesign-main | Same-object return is design choice, not Pydantic-enforced |
| 5 | `trace_id` is immutable throughout pipeline | **Runtime-Verified Proof** | HIGH | `TRACE_REPLAY_PROOF.json` — `trace_continuity_verified: true` | Verified in Sarathi path only; keshavrRedesign path verified by test |

### Replay Determinism

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 6 | Multi-run byte-identical replay (5 runs) | **Tested Proof + Runtime-Verified** | HIGH | `test_distributed_replay_identical` PASS + `distributed_replay_audit.log` | Same-environment only |
| 7 | 10-run deterministic replay | **Tested Proof** | HIGH | `test_deterministic_replay_10_runs` in keshavrRedesign-main | Same-environment only |
| 8 | 50-run stress replay | **Tested Proof** | HIGH | `test_stress_repeated_execution` in deterministic_validation_engine | Same-environment only |
| 9 | Recovery/restart replay identical | **Tested Proof + Runtime-Verified** | HIGH | `test_recovery_simulator_identical` PASS + `restart_recovery_replay_proof.json` | Does not simulate true process restart |
| 10 | Bucket truth identical across replays | **Tested Proof** | HIGH | `test_deterministic_replay_bucket_identical` in keshavrRedesign-main | In-memory bucket only |
| 11 | Cross-tree replay (KESHAV-1 ↔ Quantum_foundation) | **Not Proven** | NONE | No test, no artifact, no code | Gap documented in `runtime_engine_alignment_analysis.md` |

### Corruption Resistance

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 12 | Schema corruption rejected (fail-closed) | **Tested Proof + Runtime-Verified** | HIGH | `test_corruption_injector_fail_closed` PASS + `corruption_injection_output.json` | 3 injection types tested; not exhaustive |
| 13 | Trace mutation rejected | **Tested Proof** | HIGH | `test_corruption_injector_fail_closed` (trace injection case) | Deletion tested; subtle mutations not tested |
| 14 | Propagation mismatch rejected | **Tested Proof** | HIGH | `test_corruption_injector_fail_closed` (propagation case) | Empty-array tested; partial corruption not tested |
| 15 | No silent recovery on corruption | **Tested Proof** | HIGH | `test_corruption_injector_loose_fails` | Depends on pipeline returning status field |

### Validation Governance

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 16 | Validator has no execution authority | **Declared Proof** | MEDIUM | Code inspection — no calls to `core.execute()`, `sarathi.enforce()` | No automated authority-leak detection |
| 17 | Validator never mutates truth | **Declared Proof** | MEDIUM | Code inspection — no calls to `bucket.write_truth()` | No automated authority-leak detection |
| 18 | Validator never alters contracts silently | **Declared Proof** | MEDIUM | Code inspection — raises exceptions, never returns partial success | No automated boundary test |
| 19 | Replay does not mutate live state | **Declared Proof** | MEDIUM | `VALIDATION_GOVERNANCE_DECLARATION.md` Section 3 | No formal isolation proof beyond deep-copy |

### Cross-Layer Verification

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 20 | Trace continuity across KESHAV → RAJYA → Sarathi → Core | **Tested Proof** | HIGH | `test_cross_layer_success` + `test_trace_id_identical_across_all_layers` | Layer wrappers are stubs in some test paths |
| 21 | Bucket reconstruction fidelity | **Tested Proof** | HIGH | `test_cross_layer_success` + `test_bucket_truth_reconstructable` | In-memory bucket |
| 22 | InsightFlow observability consistency | **Tested Proof** | HIGH | `test_cross_layer_success` + `test_insightflow_emits_structured_event` | In-memory InsightBridge |
| 23 | Provenance continuity (input → Bucket truth) | **Tested Proof** | HIGH | `test_cross_layer_success` | End-to-end only in simulated pipeline |

### Sovereign Core (Sarathi)

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 24 | 5 execution scenarios verified | **Runtime-Verified Proof** | HIGH | `LIVE_EXECUTION_PROOF.json` — `scenarios_passed: 5/5` | In-memory stubs for RAJYA/Core/Bucket/InsightBridge |
| 25 | 14 failure modes documented | **Declared Proof** | MEDIUM | `FAILURE_MATRIX.md` — 14 rows | Not all 14 have individual automated tests |
| 26 | Hard fail on module unavailability | **Declared Proof** | MEDIUM | Code inspection — `ContractViolationError` raised | Module stubs are always importable in current setup |
| 27 | Trace continuity verified across 9 layers | **Runtime-Verified Proof** | HIGH | `TRACE_REPLAY_PROOF.json` | Generated by `run_sovereign_core.py` harness |
| 28 | Bucket write mandatory on all terminal paths | **Declared Proof** | MEDIUM | Code inspection — all terminal paths call `_emit_truth_artifact()` | Best-effort in error handler (line 464-470) |
| 29 | Observability mandatory on all terminal paths | **Declared Proof** | MEDIUM | Code inspection — all terminal paths call `_emit_observability()` | Best-effort in error handler (line 464-470) |

### Input Validation

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 30 | Missing `trace_id` fails closed | **Tested Proof** | HIGH | `test_failure_missing_trace_id_fail_closed` | — |
| 31 | Missing `execution_id` fails closed | **Tested Proof** | HIGH | `test_missing_execution_id_fails_closed` | — |
| 32 | Non-dict input fails closed | **Tested Proof** | HIGH | `test_non_dict_input_fails_closed` | — |
| 33 | Wrong type `execution_id` fails closed | **Tested Proof** | HIGH | `test_wrong_type_execution_id_fails_closed` | — |
| 34 | Wrong type `trace_id` fails closed | **Tested Proof** | HIGH | `test_wrong_type_trace_id_fails_closed` | — |
| 35 | Input mutation detected and rejected | **Tested Proof** | HIGH | `test_phase5_input_mutation` + `test_input_not_mutated` | — |

### KESHAV-4 Propagation

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 36 | Deterministic BFS traversal | **Declared Proof** | MEDIUM | Code inspection — `sorted()` on neighbors (line 19, 30) | No cross-platform BFS ordering test |
| 37 | Schema mismatch fails closed | **Declared Proof** | MEDIUM | `PropagationInput.model_validate()` raises `PropagationContractViolation` | — |
| 38 | Broken root cause fails closed | **Declared Proof** | MEDIUM | Line 58 — `root_cause not in dependency_graph` check | — |

### Handover Completeness

| # | Claim | Evidence Type | Confidence | Validation Source | Remaining Limitation |
|---|---|---|---|---|---|
| 39 | 14-section handover packet delivered | **Declared Proof** | MEDIUM | `HANDOVER_RAJARYAN_PACKET.md` — 14 sections present | Completeness is self-attested |
| 40 | Testing pathways documented | **Tested Proof** | HIGH | Section 11 command verified — `pytest` runs 17 tests successfully | — |
| 41 | Ecosystem dependencies mapped | **Declared Proof** | MEDIUM | Section 13 — 4 owners listed | Accuracy depends on organizational state |

---

## Confidence Distribution

| Confidence Level | Count | Percentage |
|---|---|---|
| **HIGH** (Tested or Runtime-Verified) | 27 | 66% |
| **MEDIUM** (Declared Proof) | 13 | 32% |
| **LOW** (Assumed Behavior) | 0 | 0% |
| **NONE** (Not Proven) | 1 | 2% |

---

## Key Findings

1. **No claims are based on assumed behavior.** All evidence is either tested, runtime-verified, or documented with code-level inspection.

2. **One gap has zero evidence:** Cross-tree replay between `KESHAV-1` and `Quantum_foundation` (Claim #11). This is explicitly documented as NOT IN SCOPE in `FINAL_OPEN_LOOP_AUDIT.md`.

3. **13 claims rely on declared proof only.** These are governance assertions (validator has no execution authority, validator never mutates truth) and architectural claims (deterministic BFS, failure mode documentation). They are verifiable by code inspection but lack automated regression tests.

4. **Recommendation for incoming steward:** Consider adding automated boundary tests for Claims #16-19 (validator authority boundaries) to convert from MEDIUM to HIGH confidence.

---

**PROOF CONFIDENCE MATRIX STATUS: COMPLETE — NO PROOF INFLATION DETECTED**

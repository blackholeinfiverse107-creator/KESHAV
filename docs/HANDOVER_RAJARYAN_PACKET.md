# KESHAV Convergence: Final Operational Handover Package
**To:** Rajaryan Verma (Runtime Stewardship Layer)
**From:** Kanishk / Convergence Core

This document contains the required handover package for the KESHAV convergence.

## 1. Current Architecture State
The `deterministic_validation_engine` acts as the distributed replay auditor, `keshavrRedesign-main` serves as the KESHAV Intelligence Layer, `KESHAV-4-main` as Propagation Engine, and `Sarathi` acts as the Sovereign Core Entry point. All input and output contracts are strictly enforced via the new `shared_canonical_schemas/registry.py`.

## 2. Replay Verification Flow
Replay verification is handled by `distributed_replay_engine.py`. It requires passing a trace payload through the complete pipeline (SETU → KESHAV → RAJYA → Sarathi → Core → Bucket → InsightFlow) multiple times, verifying that outputs are exactly identical and `trace_id` continuity holds.

## 3. Schema Governance Structure
All schemas are centralized in `shared_canonical_schemas/registry.py`. No downstream duplicates exist. It uses `extra="forbid"` to fail-closed on any unrecognized keys.

## 4. Validation Boundaries
The validator is strictly a read-only deterministic audit infrastructure. It does NOT own execution authority.

## 5. Constitutional Red-Lines
- No mock-only convergence allowed.
- No local schema forks.
- No trace mutation or trace drift.
- Failure MUST be fail-closed (no partial truth persistence).

## 6. Governance Drift Watchpoints
If downstream systems begin adding `.get()` parsing that ignores `ContractViolationError`, or if the canonical schemas are duplicated into local modules, this is considered drift. Watch for attempts to bypass the `Sarathi` Sovereign Core entry point directly.

## 7. Replay Reconstruction Instructions
Use `recovery_simulator.py`. Pass the original deterministic input and expected trace ID. The simulator will simulate an interruption, recreate the execution memory state, and assert that the resulting truth hash exactly matches the pre-interruption truth hash.

## 8. Common Failure Scenarios
- `ContractViolationError`: Usually missing `trace_id` or an unapproved field added to the schema.
- `TraceMutationError`: A layer intentionally or accidentally generated a new `trace_id`.
- `ReplayMismatchError`: A layer relies on random state or timestamp for logical evaluation, breaking the deterministic hash boundary.

## 9. FAQ for Incoming Maintainers
**Q: Can I add an optional field to the TANTRA output?**
A: Yes, but only in `shared_canonical_schemas/registry.py`. Local additions will cause an immediate fail-closed state.

**Q: How do I test my changes locally?**
A: Run `pytest deterministic_validation_engine/tests/` to verify you haven't broken determinism.

## 10. Full Operational Repo Structure
- `shared_canonical_schemas/`: Central Registry
- `deterministic_validation_engine/`: Audit and Proving Engine
- `Sarathi/`: Execution Orchestrator
- `keshavrRedesign-main/`: Intelligence + Observability
- `KESHAV-4-main/`: Core Propagation

## 11. Testing Pathways
Use `pytest` in the `deterministic_validation_engine/tests` folder to run all proofs:
- `test_distributed_replay.py`
- `test_recovery_replay.py`
- `test_corruption_rejection.py`
- `test_cross_layer_audit.py`

## 12. Replay Audit Explanation
Replay Audits ensure that an identical input produces an identical output across all distributed layers, proving that no layer has hidden dependencies on clock time, external I/O, or non-deterministic state.

## 13. Known Ecosystem Dependencies
- DGIC (Pritesh Patra)
- RAJYA (Rajaryan Verma)
- Sarathi (Hemanth)
- Core (Raj Prajapati)

## 14. Runtime Stewardship Expectations
As the Runtime Steward, ensure that the rules of determinism are never relaxed to bypass a failing system. Failures should result in fixing the downstream system, not relaxing the validation rules.

# Runtime / Deterministic Engine Alignment — Audit Report

## Verdict: **Partial Alignment — Strong Foundations, Critical Gaps Remain**

The project has substantial machinery for contract enforcement, deterministic replay, and runtime recovery — but the two project trees (`Quantum_foundation` and `KESHAV-1`) operate on **divergent contract models** that are not formally bridged. Below is the full breakdown.

---

## 1. Contract Layer

### What Exists ✅

| Component | Location | Purpose |
|---|---|---|
| `ExecutionEvent` / `ExecutionResult` | [interface_contract.md](file:///c:/Users/kanishk/Quantum_foundation/interface_contract.md) | Runtime input/output schema for the generic deterministic engine |
| `TantraInputContract` / `TantraOutputContract` | [registry.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/shared_canonical_schemas/registry.py) | Pydantic-enforced canonical schemas for the KESHAV validation pipeline |
| `PropagationInput` / `PropagationOutput` | [registry.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/shared_canonical_schemas/registry.py#L53-L78) | Internal propagation contracts with `extra="forbid"` |
| Dhiraj Integration Contract | [integration_contract.md](file:///c:/Users/kanishk/Quantum_foundation/integration_contract.md) | Maps domain-specific simulation output → `ExecutionEvent` payloads |
| Schema Governance | [SCHEMA_GOVERNANCE.md](file:///c:/Users/kanishk/Desktop/KESHAV-1/docs/SCHEMA_GOVERNANCE.md) | Zero-transformation rule, `trace_id` immutability, cross-repo coordination |
| Validation Governance | [VALIDATION_GOVERNANCE_DECLARATION.md](file:///c:/Users/kanishk/Desktop/KESHAV-1/docs/VALIDATION_GOVERNANCE_DECLARATION.md) | Constitutional boundaries — read-only, fail-closed, no execution authority |

### Gaps ⚠️

> [!WARNING]
> **Two disconnected contract universes**: `Quantum_foundation` uses `ExecutionEvent`/`ExecutionResult` (plain Python dataclasses in [computation_protocol.py](file:///c:/Users/kanishk/Quantum_foundation/computation_protocol.py#L38-L58)), while `KESHAV-1` uses Pydantic `TantraInputContract`/`TantraOutputContract` (in [registry.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/shared_canonical_schemas/registry.py#L18-L45)). **There is no formal adapter or mapping layer between them.**

- The `PipelineSnapshot` in [snapshot.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/snapshot.py) expects `execution_id`, `tasks`, `constraint_results`, `propagation_results`, `bottleneck_output` — this schema does **not** align with the `ExecutionEvent` schema in `Quantum_foundation`.
- The `execution_interface.py` FastAPI layer returns `{status, causal_id, state_hash, consensus}` — this does **not** match `TantraOutputContract`.

---

## 2. Replay Layer

### What Exists ✅

| Component | Location | Scope |
|---|---|---|
| Local Replay Engine | [replay_engine.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/replay_engine.py) | Snapshot → JSON roundtrip → hash match (single-node) |
| Distributed Replay Engine | [distributed_replay_engine.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/distributed_replay_engine.py) | N-run byte-identical replay across `SETU→KESHAV→RAJYA→Sarathi→Core→Bucket→InsightFlow` |
| Cross-Layer Replay Verifier | [cross_layer_verifier.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/cross_layer_verifier.py) | Trace propagation, bucket reconstruction, observability emission |
| Recovery Simulator | [recovery_simulator.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/recovery_simulator.py) | Interrupt → restart → re-run → hash-identical proof |
| Replay Hash Runner | [replay_hash_runner.py](file:///c:/Users/kanishk/Quantum_foundation/replay_hash_runner.py) | 100-iteration full-stack deterministic cycle (quantum state evolution path) |
| Reconciliation Engine | [reconciliation_engine.py](file:///c:/Users/kanishk/Quantum_foundation/reconciliation_engine.py) | Lagging node detection → missing event fetch → causal replay → hash convergence |
| Replay Proofs | [replay_reconstruction_proof.json](file:///c:/Users/kanishk/Desktop/KESHAV-1/replay_reconstruction_proof.json), [restart_recovery_replay_proof.json](file:///c:/Users/kanishk/Desktop/KESHAV-1/restart_recovery_replay_proof.json) | Documented evidence of deterministic replay passing |

### Replay Alignment Rating: **Strong within each tree, unlinked across trees**

- `KESHAV-1` replays validate the TANTRA pipeline path (constraint → propagation → bottleneck → output).
- `Quantum_foundation` replays validate the causal event sequencing path (propose → sequence → execute → reconcile).
- **Neither replay system validates the other's contracts.** If `Quantum_foundation` produced output that was consumed by `KESHAV-1`, there is no replay verification that spans that boundary.

---

## 3. Runtime Compatibility Layer

### What Exists ✅

| Component | Location | Purpose |
|---|---|---|
| `ComputationProtocolHub` | [computation_protocol.py](file:///c:/Users/kanishk/Quantum_foundation/computation_protocol.py#L225-L457) | Authoritative hub — strict causal ordering, halt-on-rejection, halt-on-divergence |
| `ProtocolNode` | [computation_protocol.py](file:///c:/Users/kanishk/Quantum_foundation/computation_protocol.py#L145-L218) | Node-level proposal + acknowledgment lifecycle |
| Execution Interface (FastAPI) | [execution_interface.py](file:///c:/Users/kanishk/Quantum_foundation/execution_interface.py) | HTTP runtime surface for event submission and metrics |
| `ReconciliationEngine` | [reconciliation_engine.py](file:///c:/Users/kanishk/Quantum_foundation/reconciliation_engine.py) | Deterministic lagging-node recovery via causal event replay |
| Drift Detector | [drift_detector.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/drift_detector.py) | Content hash, ordering, and linkage drift detection |
| Corruption Injector | [corruption_injector.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/corruption_injector.py) | Adversarial testing of snapshot corruption |
| Main Validator Orchestrator | [validator.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/validator.py) | 6-phase deterministic validation (snapshot → determinism → invariants → replay → drift → output contract) |

### Gaps ⚠️

> [!IMPORTANT]
> **No unified runtime coordinator.** The `ComputationProtocolHub` (Quantum_foundation) and the `validate_pipeline` orchestrator (KESHAV-1) are standalone systems. There is no shared runtime that:
> 1. Feeds `ExecutionResult` from the hub into `TantraInputContract` validation
> 2. Uses `TantraOutputContract` to produce an `ExecutionEvent` for downstream sequencing
> 3. Performs cross-tree replay verification

---

## 4. Summary Matrix

| Alignment Dimension | Quantum_foundation | KESHAV-1 | Cross-Tree |
|---|---|---|---|
| **Contract defined** | ✅ `ExecutionEvent`/`Result` | ✅ `TantraInput`/`OutputContract` | ❌ No mapping |
| **Contract enforced** | ✅ Halt-on-rejection | ✅ Pydantic `extra="forbid"` | ❌ Not bridged |
| **Replay — single run** | ✅ `replay_hash_runner` | ✅ `replay_engine` | ❌ Independent |
| **Replay — multi-run** | ✅ 100-iteration hash match | ✅ 5-run distributed replay | ❌ Independent |
| **Recovery / Reconciliation** | ✅ `ReconciliationEngine` | ✅ `RecoverySimulator` | ❌ Not linked |
| **Drift Detection** | ✅ Consensus divergence check | ✅ Hash + ordering + linkage | ❌ Separate mechanisms |
| **Governance docs** | ✅ Interface + Integration contracts | ✅ Schema + Validation governance | ⚠️ Governance references cross-repo but no runtime enforcement |

---

## 5. Recommendations

### Critical (must-fix for true engine alignment)

1. **Create a `ContractBridge` adapter** that maps `TantraOutputContract` ↔ `ExecutionEvent.payload` with strict Pydantic validation on both sides. This should live in a shared location (e.g., `shared_canonical_schemas/`).

2. **Build a cross-tree replay harness** that:
   - Starts from `Quantum_foundation` event submission
   - Feeds through `KESHAV-1` validation pipeline
   - Verifies deterministic output end-to-end
   - Produces a unified replay proof artifact

3. **Add a `runtime_compatibility_check.py`** that validates both contract schemas are structurally compatible at startup (field presence, types, trace_id passthrough).

### Important (hardening)

4. **Unify hashing strategies** — `Quantum_foundation` uses `repr()` + regex sanitization for hashing ([replay_hash_runner.py:19-22](file:///c:/Users/kanishk/Quantum_foundation/replay_hash_runner.py#L19-L22)), while `KESHAV-1` uses canonical JSON with `sort_keys=True` and float rounding ([snapshot.py:104-121](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/snapshot.py#L104-L121)). These are fundamentally different approaches and would produce different hashes for the same logical data.

5. **The `RecoverySimulator`** ([recovery_simulator.py](file:///c:/Users/kanishk/Desktop/KESHAV-1/deterministic_validation_engine/src/recovery_simulator.py)) simulates interruption by clearing local state — but doesn't actually simulate process restart boundaries (e.g., re-importing modules, re-initializing singletons). Consider using `subprocess` isolation for stronger recovery proof.

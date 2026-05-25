# REVIEW_PACKET.md — KESHAV TANTRA Convergence

---

## 1. Entry Point

```
analyzer/analyze_blockage.py → analyze_and_recommend(input_data)
```

Call with the INPUT CONTRACT dict. Returns the TANTRA OUTPUT CONTRACT dict.
On invalid input: returns `{ "status": "FAIL", "reason": "INVALID_INPUT_CONTRACT", "trace_id": "" }`.

---

## 2. Architecture

```
SETU/Input
  → KESHAV  (analyzer/analyze_blockage.py)   — dependency intelligence, TANTRA output contract
  → RAJYA   (tantra/rajya.py)                — decision layer, zero transformation
  → Sarathi (tantra/sarathi.py)              — enforcement layer
  → Core    (tantra/core.py)                 — execution layer
  → Bucket  (tantra/bucket.py)               — truth layer, write-on-success only

InsightFlow (tantra/insightflow.py)          — read-only observability, structured events
Pipeline    (tantra/pipeline.py)             — wires all layers, fail-closed at every step
```

---

## 3. Core Flow

```
analyzer/analyze_blockage.py       ← orchestrator: validates input, calls all phases in order
analyzer/root_cause_tracer.py      ← Phase 2: anchored to unsatisfied_dependencies, BFS for deepening
analyzer/action_generator.py       ← Phase 4: single UNBLOCK_DEPENDENCY signal for bottleneck root cause
analyzer/output_structurer.py      ← Phase 5: assembles TANTRA output with severity + timestamp
```

Full pipeline inside `analyze_and_recommend`:

```
input_data (must include trace_id)
  │
  ├─ validate()              → FAIL CLOSED if trace_id or execution_id missing/wrong type
  ├─ Phase 1   detect_blocked_tasks()      → blocked_task_ids
  ├─ Phase 2   trace_root_causes()         → root_causes (internal map)
  ├─ Phase 3   detect_bottleneck()         → bottleneck
  ├─ Phase 4   generate_actions()          → single resolution signal
  └─ Phase 5   structure_output()          → TANTRA output
```

---

## 4. Input → Output Contract

### Input (REQUIRED: trace_id + execution_id)
```json
{
  "trace_id": "upstream-trace-001",
  "execution_id": "exec-001",
  "tasks": [
    { "task_id": "T1", "depends_on": [] },
    { "task_id": "T2", "depends_on": ["T1"] },
    { "task_id": "T3", "depends_on": ["T2"] }
  ],
  "constraint_results": [
    { "task_id": "T1", "is_valid": false, "unsatisfied_dependencies": [] },
    { "task_id": "T2", "is_valid": false, "unsatisfied_dependencies": ["T1"] },
    { "task_id": "T3", "is_valid": true,  "unsatisfied_dependencies": [] }
  ],
  "propagation_results": [
    { "task_id": "T1", "affected_tasks": ["T2", "T3"], "impact_score": 10 },
    { "task_id": "T2", "affected_tasks": ["T3"],       "impact_score": 4  }
  ]
}
```

### Output (TANTRA contract — no transformation needed)
```json
{
  "trace_id": "upstream-trace-001",
  "execution_id": "exec-001",
  "root_cause": "T1",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "impact_score": 10,
  "severity": "HIGH",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### Failure Response (fail-closed)
```json
{
  "status": "FAIL",
  "reason": "INVALID_INPUT_CONTRACT",
  "trace_id": ""
}
```

---

## 5. Severity Mapping (deterministic, zero interpretation)

| Condition              | Severity |
|------------------------|----------|
| impact_score < 3       | LOW      |
| 3 ≤ impact_score < 10  | MEDIUM   |
| impact_score ≥ 10      | HIGH     |

---

## 6. What Was Built

| File | Phase | Responsibility |
|------|-------|----------------|
| `blocked_task_detector.py` | 1  | Scan constraint_results, return sorted blocked task IDs |
| `root_cause_tracer.py`     | 2  | Anchor to unsatisfied_dependencies[0]; BFS only for deepening |
| `bottleneck_detector.py`   | 3  | Max impact_score among blocked tasks, tie-break by task_id |
| `action_generator.py`      | 4  | Single `UNBLOCK_DEPENDENCY:<task_id>` signal for bottleneck root cause |
| `output_structurer.py`     | 5  | Assemble TANTRA output: trace_id passthrough, impact_score, severity, timestamp |
| `analyze_blockage.py`      | —  | Entry point: fail-closed validation, wires all phases end-to-end |
| `tantra/rajya.py`          | —  | Decision layer: consumes KESHAV output directly, zero transformation |
| `tantra/sarathi.py`        | —  | Enforcement layer: reads resolution_signal, emits enforcement record |
| `tantra/core.py`           | —  | Execution layer: executes action from Sarathi |
| `tantra/bucket.py`         | —  | Truth layer: write-on-success only, thread-safe |
| `tantra/insightflow.py`    | —  | Observability: read-only structured events |
| `tantra/pipeline.py`       | —  | Full chain orchestration: SETU → KESHAV → RAJYA → Sarathi → Core → Bucket |

---

## 7. Failure Mode Enforcement

| Condition | Response |
|-----------|----------|
| `trace_id` missing | `FAIL / INVALID_INPUT_CONTRACT` |
| `execution_id` missing | `FAIL / INVALID_INPUT_CONTRACT` |
| `trace_id` wrong type | `FAIL / INVALID_INPUT_CONTRACT` |
| `execution_id` wrong type | `FAIL / INVALID_INPUT_CONTRACT` |
| Non-dict input | `FAIL / INVALID_INPUT_CONTRACT` |

---

## 8. Edge Case Behaviour

| Case | Behaviour |
|------|-----------|
| No blocked tasks | `root_cause: null`, `resolution_signal: null`, `impact_score: 0`, `severity: LOW` |
| All tasks blocked | Highest score wins bottleneck, single signal emitted |
| Deep chain (T5→T4→T3→T2→T1) | All trace root cause back to T1; `UNBLOCK_DEPENDENCY:T1` |
| Multiple root causes | Top-level `root_cause` = bottleneck's root cause only |
| Circular dependency (T1↔T2) | `visited` set breaks loop; output deterministic |
| Self dependency (T1→T1) | `visited` set breaks loop; `root_cause = T1` |
| Missing dependency (T2→GHOST) | GHOST returned as root cause |
| Disconnected components | Bottleneck's root cause wins top-level |
| Task missing from propagation | `impact_score` defaults to 0 |

---

## 9. Full TANTRA Chain Execution Trace

### Chain
```
SETU/Input
  → KESHAV  (analyzer/analyze_blockage.py)
  → RAJYA   (tantra/rajya.py)
  → Sarathi (tantra/sarathi.py)
  → Core    (tantra/core.py)
  → Bucket  (tantra/bucket.py)
```

### Execution Trace (sample_input.json)

**Input:**
```json
{
  "trace_id": "rajya-trace-001",
  "execution_id": "exec-demo",
  "tasks": [
    { "task_id": "T1", "depends_on": [] },
    { "task_id": "T2", "depends_on": ["T1"] },
    { "task_id": "T3", "depends_on": ["T2"] }
  ],
  "constraint_results": [
    { "task_id": "T1", "is_valid": false, "unsatisfied_dependencies": [] },
    { "task_id": "T2", "is_valid": false, "unsatisfied_dependencies": ["T1"] },
    { "task_id": "T3", "is_valid": true,  "unsatisfied_dependencies": [] }
  ],
  "propagation_results": [
    { "task_id": "T1", "affected_tasks": ["T2", "T3"], "impact_score": 10 },
    { "task_id": "T2", "affected_tasks": ["T3"],       "impact_score": 4  }
  ]
}
```

**KESHAV output:**
```json
{
  "trace_id": "rajya-trace-001",
  "execution_id": "exec-demo",
  "root_cause": "T1",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "impact_score": 10,
  "severity": "HIGH",
  "timestamp": "2025-07-14T10:00:00Z"
}
```

**RAJYA output:** identical to KESHAV output (zero transformation — same object reference)

**Sarathi output:**
```json
{
  "trace_id": "rajya-trace-001",
  "enforced": true,
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
}
```

**Core output:**
```json
{
  "trace_id": "rajya-trace-001",
  "executed": true,
  "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
}
```

**Bucket stored:**
```json
{
  "trace_id": "rajya-trace-001",
  "keshav_output": { "...full KESHAV output..." },
  "core_output": { "trace_id": "rajya-trace-001", "executed": true, "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1" }
}
```

**InsightFlow event emitted:**
```json
{
  "type": "EXECUTION",
  "trace_id": "rajya-trace-001",
  "root_cause": "T1",
  "impact_score": 10,
  "severity": "HIGH",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1"
}
```

---

## 10. Zero Transformation Proof

RAJYA returns the exact same object reference as KESHAV output:
```python
assert result["rajya_output"] is result["keshav_output"]
```
No adapter, no schema mapping, no field renaming.

Test: `test_rajya_consumes_keshav_output_without_failure` — **PASS**

---

## 11. Trace Continuity Proof

`trace_id` is asserted identical at every layer:
```
Input == KESHAV == RAJYA == Sarathi == Core == Bucket == InsightFlow
```

Test: `test_trace_id_identical_across_all_layers` — **PASS**

Assertion chain from the test:
```python
assert result["keshav_output"]["trace_id"]  == expected   # KESHAV
assert result["rajya_output"]["trace_id"]   == expected   # RAJYA
assert result["sarathi_output"]["trace_id"] == expected   # Sarathi
assert result["core_output"]["trace_id"]    == expected   # Core
assert bucket.read(expected)["trace_id"]    == expected   # Bucket
assert insightflow.get_events()[0]["trace_id"] == expected  # InsightFlow
```

---

## 12. Deterministic Replay Proof (10 runs)

Same input run 10 times. Each output serialized with `json.dumps(sort_keys=True)` (timestamp excluded).
All 10 outputs are byte-for-byte identical strings.

```
test_determinism_normal_mixed            10/10 identical
test_determinism_no_blocked_tasks        10/10 identical
test_determinism_all_tasks_blocked       10/10 identical
test_determinism_deep_chain              10/10 identical
test_determinism_circular_dependency     10/10 identical
test_determinism_self_dependency         10/10 identical
test_determinism_missing_dependency      10/10 identical
test_determinism_disconnected_components 10/10 identical
test_determinism_multiple_root_causes    10/10 identical
test_input_not_mutated                   input unchanged after call

test_deterministic_replay_10_runs          10/10 identical (full pipeline)
test_deterministic_replay_bucket_identical 10/10 identical Bucket truth
```

Determinism guaranteed by:
- `sorted()` on all list outputs
- `max(..., key=lambda)` with lexicographic tie-break
- `trace_id` passed through from input — no generation, no randomness
- Severity derived purely from `impact_score` — no interpretation
- No global state

---

## 13. Parallel Execution Proof (5 concurrent flows)

```
test_rajya_five_parallel_traces   5/5 concurrent flows — all OK, all distinct trace_ids
```

5 goroutines via `ThreadPoolExecutor(max_workers=5)`, each with a unique `trace_id`.
All return `status: OK`. All trace_ids distinct.

---

## 14. InsightFlow Observability Logs

InsightFlow emits structured events at the KESHAV layer. Read-only — never mutates output.

**Successful execution event:**
```json
{
  "type": "EXECUTION",
  "trace_id": "tantra-trace-001",
  "root_cause": "T1",
  "impact_score": 10,
  "severity": "HIGH",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1"
}
```

**Failure event (missing trace_id):**
```json
{
  "type": "FAILURE",
  "trace_id": "",
  "reason": "INVALID_INPUT_CONTRACT"
}
```

**Failure event (invalid schema — non-dict):**
```json
{
  "type": "FAILURE",
  "trace_id": "",
  "reason": "INVALID_INPUT_CONTRACT"
}
```

**Failure event (corrupted propagation — trace_id omitted):**
```json
{
  "type": "FAILURE",
  "trace_id": "",
  "reason": "INVALID_INPUT_CONTRACT"
}
```

Tests:
- `test_insightflow_emits_structured_event` — **PASS**
- `test_insightflow_does_not_mutate_keshav_output` — **PASS**
- `test_insightflow_shows_failure_event` — **PASS**
- `test_failures_visible_in_insightflow` — **PASS** (3 failure events confirmed)

---

## 15. Failure Case Demonstrations

### Failure 1 — Missing trace_id
```python
run_tantra_pipeline({"execution_id": "exec-no-trace"})
# → status: FAIL
# → rajya_output: None, sarathi_output: None, core_output: None
# → Bucket: 0 entries
# → InsightFlow: FAILURE event emitted
```

### Failure 2 — Invalid schema (non-dict input)
```python
run_tantra_pipeline("not-a-dict")
# → status: FAIL
# → all downstream layers: None
# → Bucket: 0 entries
# → InsightFlow: FAILURE event emitted
```

### Failure 3 — Corrupted propagation (trace_id omitted from payload)
```python
run_tantra_pipeline({
    "execution_id": "exec-corrupted",
    # trace_id intentionally omitted
    "tasks": [...],
    "constraint_results": [...],
    "propagation_results": [...]
})
# → status: FAIL
# → all downstream layers: None
# → Bucket: 0 entries
# → InsightFlow: FAILURE event emitted
```

All 3 failures:
- Fail-closed: no partial execution
- No write to Bucket
- Visible in InsightFlow as `FAILURE` events

Tests:
- `test_failure_missing_trace_id_fail_closed` — **PASS**
- `test_failure_invalid_schema_fail_closed` — **PASS**
- `test_failure_corrupted_propagation_no_bucket_write` — **PASS**
- `test_no_partial_execution_on_failure` — **PASS**
- `test_failed_runs_not_in_bucket` — **PASS**

---

## 16. Bucket Verification Proof

Successful runs are stored in Bucket keyed by `trace_id` and are fully retrievable.

```python
bucket.read("tantra-trace-001")
# Returns:
{
  "trace_id": "tantra-trace-001",
  "keshav_output": {
    "trace_id": "tantra-trace-001",
    "execution_id": "exec-tantra-001",
    "root_cause": "T1",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 10,
    "severity": "HIGH",
    "timestamp": "..."
  },
  "core_output": {
    "trace_id": "tantra-trace-001",
    "executed": true,
    "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
  }
}
```

Truth is reconstructable: `root_cause`, `resolution_signal`, `impact_score`, `severity` all present.

Tests:
- `test_successful_run_stored_in_bucket` — **PASS**
- `test_bucket_truth_reconstructable` — **PASS**
- `test_deterministic_replay_bucket_identical` — **PASS** (10/10 identical)

---

## 17. TANTRA Convergence Test Results

```
Phase 1 — RAJYA Integration
  test_rajya_consumes_keshav_output_without_failure   PASS
  test_rajya_five_parallel_traces                     PASS (5 concurrent)

Phase 2 — InsightFlow Observability
  test_insightflow_emits_structured_event             PASS
  test_insightflow_does_not_mutate_keshav_output      PASS
  test_insightflow_shows_failure_event                PASS

Phase 3 — Full TANTRA Chain
  test_full_tantra_chain_all_layers_active            PASS
  test_full_chain_keshav_output_contract              PASS
  test_full_chain_sarathi_consumes_resolution_signal  PASS
  test_full_chain_core_executes_action                PASS

Phase 4 — Trace Continuity
  test_trace_id_identical_across_all_layers           PASS
  test_trace_id_in_insightflow_event                  PASS

Phase 5 — Deterministic Replay
  test_deterministic_replay_10_runs                   PASS (10/10)
  test_deterministic_replay_bucket_identical          PASS (10/10)

Phase 6 — Failure + Truth Verification
  test_failure_missing_trace_id_fail_closed           PASS
  test_failure_invalid_schema_fail_closed             PASS
  test_failure_corrupted_propagation_no_bucket_write  PASS
  test_failures_visible_in_insightflow                PASS
  test_no_partial_execution_on_failure                PASS
  test_successful_run_stored_in_bucket                PASS
  test_bucket_truth_reconstructable                   PASS
  test_failed_runs_not_in_bucket                      PASS
  test_pipeline_sarathi_failure_is_fail_closed        PASS
  test_pipeline_core_failure_is_fail_closed           PASS
  test_pipeline_rajya_trace_mismatch_is_fail_closed   PASS

Total: 24/24 TANTRA convergence tests passing
```

---

## 18. Full Test Suite Results

```
123 passed in 0.75s — 100% coverage (analyzer + tantra)

tests/test_layer_contracts.py     9 tests  — all PASS
tests/test_phase1.py              8 tests  — all PASS
tests/test_phase2.py              9 tests  — all PASS
tests/test_phase3.py              9 tests  — all PASS
tests/test_phase5.py             13 tests  — all PASS
tests/test_phase6.py             11 tests  — all PASS
tests/test_phase7.py              9 tests  — all PASS
tests/test_phase8.py             10 tests  — all PASS
tests/test_tantra_convergence.py 24 tests  — all PASS
tests/test_validation.py          8 tests  — all PASS
tests/test_production.py         13 tests  — all PASS

Coverage:
  analyzer/   100%
  tantra/     100%
  TOTAL       100%
```

---

## 19. Production Hardening

### What was hardened

| Area | Change | Reason |
|------|--------|--------|
| `analyze_blockage.py` | Validate list fields (`tasks`, `constraint_results`, `propagation_results`) | Malformed non-list values caused unhandled `TypeError` deep in pipeline |
| `tantra/pipeline.py` | `except Exception` instead of `except ValueError` at each layer boundary | Non-`ValueError` layer exceptions propagated uncaught to Flask as 500 |
| `tantra/insightflow.py` | `MAX_EVENTS = 10_000` cap with oldest-eviction; `logger.warning` for failures | Unbounded list caused OOM under sustained load |
| `tantra/bucket.py` | `MAX_ENTRIES = 50_000` cap with oldest-eviction | Unbounded dict caused OOM under sustained load |
| `api.py` | `MAX_CONTENT_LENGTH` (1 MB default via `MAX_CONTENT_MB` env var); 413/404/405/500 JSON error handlers; removed deprecated `JSON_SORT_KEYS` config | Request size limit prevents memory exhaustion; structured error responses for all failure modes |
| `pyproject.toml` | `flask>=3.0,<4`; added `gunicorn>=22.0` | Pin Flask major version; gunicorn required for production WSGI serving |
| `Makefile` | Added `run-prod` target | `python api.py` uses Flask dev server — not safe for production |
| `.env.example` | Added | Operators need documented env vars |

### Production run

```bash
pip install -e ".[dev]"
make run-prod
# gunicorn "api:app" --workers 4 --bind 0.0.0.0:5000
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Bind address (dev server only) |
| `PORT` | `5000` | Listening port (dev server only) |
| `DEBUG` | `false` | Flask debug mode (dev server only) |
| `MAX_CONTENT_MB` | `1` | Max request body size in MB |

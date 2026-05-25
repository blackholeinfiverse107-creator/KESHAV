# Orchestration Boundary Charter
**Date:** 2025-07-15
**Owner:** Akanksha Parab — Sovereign Core Integration Layer
**Status:** CONSTITUTIONAL LOCK

---

## A. What Sovereign Core Orchestration OWNS

| Responsibility | Description |
|---|---|
| Entry point | `invoke_sovereign_core()` — single, non-duplicable |
| trace_id generation | Generated ONCE at entry, never regenerated |
| Mandala Object lifecycle | Created at entry, fields appended per layer, returned at terminal |
| Call ordering | DGIC → PDE → RAJYA → Sarathi → Enforcement → Core → Bucket → InsightBridge |
| Contract validation | `execution_contract_validator.py` — field presence, execution_id continuity, trace immutability |
| Truth emission trigger | Calls `_emit_truth_artifact()` at every terminal path |
| Observability emission trigger | Calls `_emit_observability()` at every terminal path |
| Failure propagation | Hard fail via ContractViolationError with trace_id in message |

---

## B. What Sovereign Core Orchestration DOES NOT OWN

| Domain | Owner | Why Sovereign Core Cannot Touch It |
|---|---|---|
| Threat reasoning | DGIC (Pritesh Patra) | Reasoning authority belongs to DGIC |
| Policy rules | `policies.json` / PDE | Policy is external config, not orchestration logic |
| Final execution authority | RAJYA (Rajaryan Verma) | RAJYA is the authority layer — orchestration only passes data |
| Enforcement token | Sarathi (Hemanth) | Token minting is Sarathi's exclusive responsibility |
| Non-bypassable gate | `enforcement.enforce_decision()` | Gate logic belongs to Sarathi layer |
| Execution sink | Core (Raj Prajapati) | Core decides what "execution" means |
| Truth storage implementation | Bucket (Infrastructure) | Persistence backend is infrastructure concern |
| Observability routing | InsightBridge (Infrastructure) | Stream routing is infrastructure concern |

---

## C. Prohibited Authority Escalation Paths

The following are constitutionally prohibited:

1. **Orchestration making policy decisions** — `sovereign_core_entry.py` must never evaluate `confidence`, `epistemic_state`, or `collapse_trigger` directly. That is PDE's job.

2. **Orchestration overriding RAJYA** — If RAJYA returns `REJECT`, execution stops. Orchestration cannot retry, reroute, or override.

3. **Orchestration minting tokens** — Only `sarathi_engine.evaluate()` produces tokens. Orchestration cannot construct a token manually.

4. **Orchestration reading InsightBridge output** — InsightBridge is write-only from the execution path. No query result from InsightBridge may influence routing.

5. **Orchestration writing truth directly** — Truth artifacts must go through `truth_contracts.build_truth_artifact()` and `bucket.write_truth()`. Orchestration cannot write raw dicts to Bucket.

6. **Orchestration absorbing enforcement** — `enforce_decision()` must always be called. Orchestration cannot short-circuit it based on its own assessment.

---

## D. Forbidden Hidden-State Regions

| Region | Why Forbidden |
|---|---|
| In-memory execution cache | Would create hidden governance-bearing state outside Bucket |
| Mutable truth store | Bucket is append-only — no overwrite permitted |
| Orchestration-local policy cache | Policy must always come from `policies.json` via `policy_loader` |
| Trace regeneration | trace_id generated once — any regeneration is a constitutional violation |
| Silent fallback execution | If a module is unavailable, hard fail — no silent degradation |
| Observability-driven routing | InsightBridge output must never feed back into execution decisions |

---

## E. Constitutionally Invalid Runtime Couplings

| Coupling | Why Invalid |
|---|---|
| Orchestration → RAJYA bypass | RAJYA is the final authority — no path around it |
| InsightBridge → Orchestration feedback loop | Observability is one-way — read-back creates hidden authority |
| Bucket → Orchestration state restoration | Bucket is truth record — not a state restoration mechanism for live execution |
| PDE → Enforcement direct coupling | PDE recommends, RAJYA decides, Sarathi enforces — no shortcut |
| Orchestration → Core without Sarathi token | Core must only be called after `enforce_decision()` returns True |
| Trace mutation → continued execution | Any trace mutation must hard fail — no recovery path |

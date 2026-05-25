# Runtime Authority Matrix
**Date:** 2025-07-15
**Phase:** TANTRA Constitutional Boundary Lock

---

## Authority Ownership

| Decision | Owner | Module | Sovereign Core Role |
|---|---|---|---|
| Threat analysis | DGIC | `dgic.analyze()` | Pass ksml_input, receive dgic_reasoning |
| Policy evaluation | PDE | `pde_engine.evaluate()` | Pass pde_payload, receive policy_decision |
| Final execution authority | RAJYA | `rajya.validate()` | Pass policy_decision, receive verdict |
| Enforcement token mint | Sarathi | `sarathi_engine.evaluate()` | Pass sarathi_payload, receive token |
| Non-bypassable gate | Sarathi/Enforcement | `enforcement.enforce_decision()` | Call unconditionally, receive bool |
| Execution | Core | `core.execute()` | Pass sarathi_token, receive result |
| Truth persistence | Bucket | `bucket.write_truth()` | Trigger write, never read back into execution |
| Observability | InsightBridge | `insightbridge.emit()` | Trigger emit, never read back into execution |

---

## Sovereignty Boundaries

```
┌─────────────────────────────────────────────────────────┐
│  SOVEREIGN CORE ORCHESTRATION BOUNDARY                  │
│                                                         │
│  OWNS: entry, trace_id, call order, contract validation │
│  DOES NOT OWN: any authority decision                   │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  DGIC    │  │  RAJYA   │  │  Core    │             │
│  │ Pritesh  │  │ Rajaryan │  │  Raj     │             │
│  │ EXTERNAL │  │ EXTERNAL │  │ EXTERNAL │             │
│  └──────────┘  └──────────┘  └──────────┘             │
│                                                         │
│  ┌──────────┐  ┌──────────┐                           │
│  │  PDE     │  │ Sarathi  │                           │
│  │ Akanksha │  │ Hemanth  │                           │
│  │IN-PROCESS│  │IN-PROCESS│                           │
│  └──────────┘  └──────────┘                           │
│                                                         │
│  ┌──────────┐  ┌──────────────┐                       │
│  │  Bucket  │  │ InsightBridge│                       │
│  │  INFRA   │  │    INFRA     │                       │
│  └──────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## Runtime Failure Authority

| Failure | Who Decides Recovery |
|---|---|
| DGIC unavailable | Operator — no automatic recovery |
| RAJYA REJECT | RAJYA — orchestration stops, does not retry |
| Sarathi BLOCK | Sarathi/Enforcement — orchestration stops |
| Core failure | Core — orchestration records failure, does not retry |
| Bucket failure | Operator — truth persistence is mandatory |
| InsightBridge failure | Operator — observability is mandatory |
| Trace mutation | Orchestration — hard fail, no recovery |

---

## Immutable Invariants

These cannot be changed without a constitutional amendment:

1. `trace_id` generated once at `invoke_sovereign_core()` entry
2. RAJYA REJECT always stops execution — no override
3. `enforce_decision()` always called before Core
4. Bucket write always called at every terminal path
5. InsightBridge emit always called at every terminal path
6. PDE never calls `enforce_decision()` directly
7. Orchestration never reads from InsightBridge
8. Bucket is append-only — no overwrite

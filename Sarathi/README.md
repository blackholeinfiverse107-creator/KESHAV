# SARATHI - Policy-Driven Decision Engine

**Sarathi** is a strict, policy-driven decision engine that evaluates execution requests against external policies and enforces non-bypassable decisions.

## Quick Start

```bash
# Run full test suite (all 8 test cases)
python main.py run-tests

# Run interactive demo
python main.py demo

# Show help
python main.py help
```

## Architecture

```
DGIC (Threat Analysis)
        ↓
    [payload with signals]
        ↓
sarathi_engine.evaluate()
    [decision: ALLOW|DENY|ESCALATE]
        ↓
enforcement.core_gate()
    [authorized: true|false]
        ↓
    [Core Ready / Core Rejected]
```

## Core Components

### 1. **Input Contract** (`decision_contract.py`)
Validates all incoming requests against a strict schema:

```python
payload = {
    "execution_id": "string",           # Required, unique
    "dgic_output": {                    # Required, must contain:
        "confidence": float,            # 0.0-1.0
        "epistemic_state": string,      # "resolved", "conflict", etc.
        "collapse_trigger": bool        # true|false
    },
    "execution_hash": "sha256_hex",    # SHA256 hash of dgic_output
    "timestamp": "ISO8601_string"       # When request was made
}
```

**Validation Rules:**
- ✅ All keys present
- ✅ execution_id non-empty
- ✅ dgic_output is dict with required fields
- ✅ Hash matches SHA256(dgic_output)

**Violations** → DENY

---

### 2. **Policy Registry** (`policies.json`)
External, replaceable policy configuration — **NO hardcoded rules**:

```json
{
  "version": "1.0.0",
  "confidence_threshold": 0.7,
  "deny_conditions": ["hash_mismatch", "invalid_schema", "missing_execution_id"],
  "escalation_conditions": ["low_confidence", "conflict", "policy_missing", "undefined_condition"],
  "allow_conditions": ["all_validations_passed"]
}
```

**To Update:** Edit `policies.json` directly — **no code changes needed**

---

### 3. **Decision Engine** (`sarathi_engine.py`)
Evaluates requests against policies:

```python
decision = evaluate(payload, policy_path=None)
```

**Returns:**
```json
{
  "execution_id": "string",
  "decision": "ALLOW|DENY|ESCALATE",
  "reason": "string",
  "confidence": float,
  "policy_version": "string",
  "timestamp": "ISO8601_string"
}
```

---

### 4. **Enforcement Layer** (`enforcement.py`)
Non-bypassable gate — **only ALLOW decisions proceed**:

```python
authorized = enforce_decision(execution_id, sarathi_decision)
# True → Core can execute
# False → Core rejects (by design)

# Or use complete gate:
gate = core_gate(execution_id, payload, policy_path=None)
# gate.authorized tells Core if execution is safe
```

---

## Decision Rules

### 🔴 DENY (Highest Priority)
Decision stops execution immediately:
| Condition | Trigger |
|-----------|---------|
| Hash mismatch | execution_hash ≠ SHA256(dgic_output) |
| Invalid schema | Missing required fields |
| Missing execution_id | execution_id is empty/null |

### 🟡 ESCALATE (Human Review)
Execution paused for human decision:
| Condition | Trigger |
|-----------|---------|
| Low confidence | confidence < threshold (0.7) |
| Conflicting signals | epistemic_state == "conflict" OR collapse_trigger == true |
| Policy missing | Policy file not found |
| Undefined condition | Policy condition not recognized |

### 🟢 ALLOW (Authorized)
Execution proceeds:
| Condition | Trigger |
|-----------|---------|
| All validations passed | All contract checks pass + policy satisfied + high confidence |

---

## Test Suite

8 comprehensive test cases covering all requirements:

```bash
python main.py run-tests

# Output:
# ✅ Case 1: Hash Mismatch → DENY
# ✅ Case 2: Missing execution_id → DENY
# ✅ Case 3: Low Confidence → ESCALATE
# ✅ Case 4: Policy Missing → ESCALATE
# ✅ Case 5: Conflicting Signals → ESCALATE
# ✅ Case 6: Success (ALLOW)
# ✅ Case 7: Enforcement Gate (DENY)
# ✅ Case 8: Enforcement Gate (ALLOW)
```

---

## Example Usage

### Scenario 1: Normal Execution (ALLOW)

```python
import hashlib
import json
from sarathi_engine import evaluate
from enforcement import core_gate

# Create payload
dgic_output = {
    "confidence": 0.85,
    "epistemic_state": "resolved",
    "collapse_trigger": False
}

payload = {
    "execution_id": "req_12345",
    "dgic_output": dgic_output,
    "execution_hash": hashlib.sha256(
        json.dumps(dgic_output, sort_keys=True).encode()
    ).hexdigest(),
    "timestamp": "2026-04-08T10:30:00Z"
}

# Get decision
decision = evaluate(payload)
print(decision["decision"])  # "ALLOW"

# Enforce it (gate for Core)
gate = core_gate("req_12345", payload)
if gate["authorized"]:
    print("✅ Core can execute")
else:
    print("❌ Core execution blocked")
```

### Scenario 2: Low Confidence (ESCALATE)

```python
# Same payload, but confidence = 0.5
payload["dgic_output"]["confidence"] = 0.5
payload["execution_hash"] = hashlib.sha256(
    json.dumps(payload["dgic_output"], sort_keys=True).encode()
).hexdigest()

decision = evaluate(payload)
print(decision["decision"])      # "ESCALATE"
print(decision["reason"])        # "low_confidence"

gate = core_gate("req_12345", payload)
print(gate["authorized"])        # False
# Core rejects execution, request goes to human reviewer
```

### Scenario 3: Tampered Hash (DENY)

```python
payload["execution_hash"] = "tampered_xyz_invalid"

decision = evaluate(payload)
print(decision["decision"])      # "DENY"
print(decision["reason"])        # "hash_mismatch"

gate = core_gate("req_12345", payload)
print(gate["authorized"])        # False
# Core rejects execution immediately (security violation)
```

---

## Requirements Checklist

| Req | Requirement | Status |
|-----|-------------|--------|
| 1 | Input Contract (LOCKED) | ✅ Implemented |
| 2 | Policy Registry (EXTERNAL) | ✅ Implemented |
| 3 | Signal + Risk Interpretation (LIMITED) | ✅ Implemented |
| 4 | Decision Engine (FINAL AUTHORITY) | ✅ Implemented |
| 5 | Decision Rule Framework | ✅ Implemented |
| 6 | Non-bypassability (STRICT) | ✅ Implemented |
| 7 | Enforcement Relationship | ✅ Implemented |
| 8 | Failure Cases (MANDATORY) | ✅ All 5 + 3 more |
| 9 | No Violations | ✅ Verified |

---

## Key Design Principles

1. **Policy-Driven**: All rules in `policies.json` — no hardcoded logic
2. **Non-Bypassable**: Enforcement layer blocks unauthorized execution
3. **Stateless**: Each request independently evaluated
4. **Deterministic**: Same input always produces same decision
5. **Auditable**: Full execution_id tracing in all decisions
6. **Strict**: DENY has highest priority; conflict → ESCALATE

---

## File Structure

```
Sarathi/
├── main.py                    # Entry point (run-tests, demo, help)
├── sarathi_engine.py          # Core decision engine
├── decision_contract.py       # Input validation
├── policy_loader.py           # Policy file loading
├── policies.json              # External policies (EDITABLE)
├── enforcement.py             # Non-bypassable gate
├── test_sarathi.py           # 8 comprehensive test cases
├── README.md                  # This file
└── requirements.txt           # Python dependencies (none needed!)
```

---

## No External Dependencies

Sarathi uses **only Python 3.9+ standard library**:
- `json` - Policy loading
- `hashlib` - Hash validation
- `datetime` - Timestamping
- `os` - File operations

**No pip installs needed!**

---

## Running the Engine

### Option 1: Run All Tests
```bash
python main.py run-tests
```
Verifies all 8 test cases pass (failures marked as ❌, successes as ✅)

### Option 2: Interactive Demo
```bash
python main.py demo
```
Shows 3 live scenarios:
1. Normal ALLOW case
2. Escalation (low confidence)
3. Denial (hash mismatch)

### Option 3: Use in Your Code
```python
from sarathi_engine import evaluate
from enforcement import core_gate

# Get decision
decision = evaluate(payload)

# Gate for Core
gate = core_gate(execution_id, payload)
if gate["authorized"]:
    # Core proceeds
else:
    # Core stops
```

---

## Questions?

- **How to change policies?** → Edit `policies.json`
- **How to add new signals?** → Modify `dgic_output` schema in `decision_contract.py`
- **How to test a specific case?** → Run `python test_sarathi.py` then call specific test functions
- **How does Core integrate?** → Core checks `gate["authorized"]` before executing

---

**Status**: ✅ COMPLETE - All 9 requirements implemented and tested

import sys
import json
from pde_engine import evaluate
from pde_contract import compute_hash
from test_pde import run_all_tests


def _make_payload(execution_id, confidence=0.85, epistemic_state="resolved", collapse_trigger=False):
    dgic = {
        "decision": "ALLOW",
        "confidence": confidence,
        "epistemic_state": epistemic_state,
        "reason_trace": [],
        "collapse_trigger": collapse_trigger,
    }
    dgic["execution_hash"] = compute_hash(execution_id, dgic)
    return {"execution_id": execution_id, "dgic_reasoning": dgic}


def demo():
    print("\n" + "=" * 70)
    print("POLICY DECISION ENGINE (PDE) — DEMO")
    print("=" * 70)

    scenarios = [
        ("ALLOW  — high confidence, resolved", _make_payload("demo_001")),
        ("ESCALATE — low confidence",          _make_payload("demo_002", confidence=0.5)),
        ("ESCALATE — collapse_trigger",        _make_payload("demo_003", collapse_trigger=True)),
    ]

    # DENY scenario: tampered hash
    deny_payload = _make_payload("demo_004")
    deny_payload["dgic_reasoning"]["execution_hash"] = "tampered"
    scenarios.append(("DENY   — hash mismatch (tampered)", deny_payload))

    for label, payload in scenarios:
        print(f"\n[{label}]")
        print(f"Input:  {json.dumps(payload, indent=2)}")
        result = evaluate(payload)
        print(f"Output: {json.dumps(result, indent=2)}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE — output ready for RAJYA")
    print("=" * 70)


def show_help():
    print("""
POLICY DECISION ENGINE (PDE)
==============================
Consumes DGIC reasoning, applies policy logic, produces structured
recommendation for RAJYA. PDE is NOT an authority layer.

USAGE:
  python main.py run-tests    # Run full test suite
  python main.py demo         # Run demo scenarios
  python main.py help         # Show this help

INTEGRATION:
  Input  ← DGIC (Pritesh Patra)
  Output → RAJYA (Rajaryan Verma) for final validation
  Enforcement is handled by Sarathi (Hemanth) — separate system

OUTPUT SHAPE:
  {
    "execution_id": "...",
    "policy_decision": {
      "decision": "ALLOW | DENY | ESCALATE",
      "reason": "...",
      "confidence": 0.0,
      "policy_version": "...",
      "timestamp": "ISO8601",
      "decision_hash": "sha256hex"
    }
  }
""")


def main():
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    if cmd == "run-tests":
        sys.exit(0 if run_all_tests() else 1)
    elif cmd == "demo":
        demo()
    else:
        show_help()


if __name__ == "__main__":
    main()

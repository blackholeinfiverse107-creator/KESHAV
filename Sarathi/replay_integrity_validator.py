"""
replay_integrity_validator.py
Phase 3 — Replay Integrity Validator

Tests all replay conditions:
- Full replay determinism
- Partial runtime failure
- Delayed / missing observability
- Stale replay artifact
- Corrupted lineage chain

Run: python replay_integrity_validator.py
"""

import json
import sys
import copy
from datetime import datetime, timezone

from pde_contract import compute_hash as pde_compute_hash
from sovereign_core_entry import invoke_sovereign_core
from distributed_trace_federation import build_lineage_artifact, validate_lineage
from replay_federation import validate_replay, detect_corruption, reconstruct_degraded

import bucket
import insightbridge


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _make_request(execution_id: str, confidence=0.85, epistemic_state="resolved",
                  collapse_trigger=False) -> dict:
    dgic = {
        "decision": "ALLOW",
        "confidence": confidence,
        "epistemic_state": epistemic_state,
        "reason_trace": [],
        "collapse_trigger": collapse_trigger,
    }
    dgic["execution_hash"] = pde_compute_hash(execution_id, dgic)
    return {
        "execution_id": execution_id,
        "ksml_input": {"dgic_reasoning": dgic},
    }


def _run(label: str, fn) -> dict:
    print(f"\n{'─'*60}")
    print(f"TEST: {label}")
    print(f"{'─'*60}")
    try:
        result = fn()
        status = "PASS" if result.get("passed", True) else "FAIL"
        print(f"  Result: {status}")
        if not result.get("passed", True):
            print(f"  Reason: {result.get('reason', '—')}")
        return {"label": label, "status": status, "result": result}
    except Exception as e:
        print(f"  Result: ERROR — {e}")
        return {"label": label, "status": "ERROR", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────
# Test Conditions
# ─────────────────────────────────────────────────────────────────────────

def test_full_replay_determinism():
    """
    Run the same logical execution twice.
    Verify: same dgic_output hash, same pde decision, same execution status.
    Note: trace_ids will differ (each execution gets a new one) — that is correct.
    Determinism = same inputs → same outputs, not same trace_id.
    """
    req1 = _make_request("replay_det_001")
    req2 = _make_request("replay_det_001")  # identical input

    m1 = invoke_sovereign_core(req1)
    m2 = invoke_sovereign_core(req2)

    import hashlib, json
    h1_dgic = hashlib.sha256(json.dumps(m1.get("dgic_output", {}), sort_keys=True, default=str).encode()).hexdigest()
    h2_dgic = hashlib.sha256(json.dumps(m2.get("dgic_output", {}), sort_keys=True, default=str).encode()).hexdigest()

    status1 = m1.get("execution_result", {}).get("status")
    status2 = m2.get("execution_result", {}).get("status")

    passed = (h1_dgic == h2_dgic) and (status1 == status2)
    print(f"  dgic_hash match:   {h1_dgic == h2_dgic}")
    print(f"  status match:      {status1} == {status2} → {status1 == status2}")
    return {"passed": passed, "dgic_hash_match": h1_dgic == h2_dgic,
            "status_match": status1 == status2}


def test_partial_runtime_failure():
    """
    Simulate partial runtime: execution reaches RAJYA REJECT (no Core called).
    Verify: truth artifact still written, observability still emitted,
    lineage valid for reachable layers.
    """
    req = _make_request("replay_partial_001", confidence=0.3)  # low → ESCALATE → REJECT
    m = invoke_sovereign_core(req)

    status = m.get("execution_result", {}).get("status")
    truth_written = m.get("truth_artifact") is not None
    obs_emitted = m.get("observability") is not None
    lineage = validate_lineage(m)

    passed = (status == "REJECTED") and truth_written and obs_emitted and lineage["valid"]
    print(f"  status:            {status}")
    print(f"  truth_written:     {truth_written}")
    print(f"  obs_emitted:       {obs_emitted}")
    print(f"  lineage_valid:     {lineage['valid']}")
    print(f"  missing_layers:    {lineage['missing']}")
    return {"passed": passed, "status": status, "truth_written": truth_written,
            "obs_emitted": obs_emitted, "lineage_valid": lineage["valid"],
            "missing_layers": lineage["missing"]}


def test_delayed_observability():
    """
    Simulate delayed observability: observability field removed from mandala.
    Verify: truth artifact still valid for replay (observability is not required
    for truth verification — it is required for emission but not for replay proof).
    """
    req = _make_request("replay_obs_001")
    m = invoke_sovereign_core(req)

    truth = m.get("truth_artifact", {})
    # Remove observability to simulate delayed/missing telemetry
    m_degraded = copy.deepcopy(m)
    m_degraded.pop("observability", None)

    # Reconstruct from truth artifact with observability missing
    recon = reconstruct_degraded(
        truth,
        available_layers=["dgic", "pde", "rajya", "sarathi", "enforcement", "core", "bucket"]
    )

    passed = (
        recon["verifiable"].get("trace_id") == m["trace_id"] and
        recon["verifiable"].get("execution_status") is not None and
        "observability" in recon["missing_layers"]
    )
    print(f"  trace_id verified: {recon['verifiable'].get('trace_id') == m['trace_id']}")
    print(f"  status verified:   {recon['verifiable'].get('execution_status')}")
    print(f"  missing_layers:    {recon['missing_layers']}")
    return {"passed": passed, "reconstruction": recon}


def test_stale_replay_artifact():
    """
    Simulate stale artifact: truth artifact has old execution_status.
    Verify: corruption detector catches the mismatch.
    """
    req = _make_request("replay_stale_001")
    m = invoke_sovereign_core(req)

    # Stale artifact: tamper execution_status
    stale_truth = copy.deepcopy(m.get("truth_artifact", {}))
    stale_truth["execution_status"] = "STALE_STATUS"

    corruption = detect_corruption(stale_truth, m)

    passed = corruption["corrupted"] and any(
        c["field"] == "execution_status" for c in corruption["corruptions"]
    )
    print(f"  corrupted:         {corruption['corrupted']}")
    print(f"  corruptions:       {[c['field'] for c in corruption['corruptions']]}")
    return {"passed": passed, "corruption": corruption}


def test_corrupted_lineage_chain():
    """
    Simulate corrupted lineage: tamper trace_id in one layer output.
    Verify: lineage validator detects the break.
    """
    req = _make_request("replay_corrupt_001")
    m = invoke_sovereign_core(req)

    # Corrupt the rajya_verdict trace_id
    m_corrupted = copy.deepcopy(m)
    if m_corrupted.get("rajya_verdict"):
        m_corrupted["rajya_verdict"]["trace_id"] = "corrupted_trace_xyz"

    lineage = validate_lineage(m_corrupted)

    passed = not lineage["valid"] and "rajya" in lineage["breaks"]
    print(f"  lineage_valid:     {lineage['valid']}")
    print(f"  breaks:            {lineage['breaks']}")
    return {"passed": passed, "breaks": lineage["breaks"]}


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────

def run_all() -> dict:
    print("\n" + "="*60)
    print("REPLAY INTEGRITY VALIDATOR")
    print("Phase 3 — Distributed Replay-Safe Execution Proof")
    print("="*60)

    bucket.clear_truths()
    insightbridge.clear_log()

    tests = [
        ("Full Replay Determinism",      test_full_replay_determinism),
        ("Partial Runtime Failure",       test_partial_runtime_failure),
        ("Delayed Observability",         test_delayed_observability),
        ("Stale Replay Artifact",         test_stale_replay_artifact),
        ("Corrupted Lineage Chain",       test_corrupted_lineage_chain),
    ]

    results = []
    for label, fn in tests:
        results.append(_run(label, fn))

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed")
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {r['label']}")
    print(f"{'='*60}\n")

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "results": results,
    }

    with open("REPLAY_INTEGRITY_PROOF.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print("✅ REPLAY_INTEGRITY_PROOF.json written")

    return summary


if __name__ == "__main__":
    result = run_all()
    sys.exit(0 if result["all_passed"] else 1)

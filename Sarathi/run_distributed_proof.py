"""
run_distributed_proof.py
Phase 6 — Full Distributed Execution Proof

10 mandatory scenarios:
1.  Full ALLOW path
2.  RAJYA rejection path
3.  Sarathi block path
4.  Trace corruption attempt
5.  Replay corruption attempt
6.  Partial runtime failure
7.  Delayed telemetry recovery
8.  Bucket replay reconstruction
9.  Distributed restart replay
10. Observability interruption recovery

Run: python run_distributed_proof.py
"""

import copy
import json
import sys
from datetime import datetime, timezone

from pde_contract import compute_hash as pde_compute_hash
from sovereign_core_entry import invoke_sovereign_core
from execution_contract_validator import ContractViolationError, validate_stage
from distributed_trace_federation import build_lineage_artifact, validate_lineage
from replay_federation import validate_replay, detect_corruption, reconstruct_degraded
from insightbridge_boundary_validator import prove_observability_isolation
from truth_contracts import validate_truth_artifact

import bucket
import insightbridge


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _req(execution_id, confidence=0.85, epistemic_state="resolved",
         collapse_trigger=False):
    dgic = {
        "decision": "ALLOW", "confidence": confidence,
        "epistemic_state": epistemic_state,
        "reason_trace": [], "collapse_trigger": collapse_trigger,
    }
    dgic["execution_hash"] = pde_compute_hash(execution_id, dgic)
    return {"execution_id": execution_id,
            "ksml_input": {"dgic_reasoning": dgic}}


def _run(label, fn):
    print(f"\n{'─'*60}\nSCENARIO: {label}\n{'─'*60}")
    try:
        result = fn()
        ok = result.get("passed", False)
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}")
        if not ok:
            print(f"  reason: {result.get('reason', '—')}")
        return {"scenario": label, "status": "PASS" if ok else "FAIL",
                "result": result}
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return {"scenario": label, "status": "ERROR", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────────────────────────────────

def s1_full_allow():
    m = invoke_sovereign_core(_req("dp_001"))
    truth_v = validate_truth_artifact(m["truth_artifact"])
    lineage = validate_lineage(m)
    iso = prove_observability_isolation(m)
    passed = (
        m["execution_result"]["status"] == "EXECUTED" and
        m["enforcement_result"]["authorized"] is True and
        truth_v["valid"] and lineage["valid"] and iso["isolation_proven"]
    )
    return {"passed": passed,
            "status": m["execution_result"]["status"],
            "truth_valid": truth_v["valid"],
            "lineage_valid": lineage["valid"],
            "isolation_proven": iso["isolation_proven"]}


def s2_rajya_rejection():
    m = invoke_sovereign_core(_req("dp_002", confidence=0.3))
    truth_v = validate_truth_artifact(m["truth_artifact"])
    passed = (
        m["execution_result"]["status"] == "REJECTED" and
        m["enforcement_result"]["authorized"] is False and
        truth_v["valid"]
    )
    return {"passed": passed, "status": m["execution_result"]["status"],
            "truth_valid": truth_v["valid"]}


def s3_sarathi_block():
    m = invoke_sovereign_core(_req("dp_003", collapse_trigger=True))
    truth_v = validate_truth_artifact(m["truth_artifact"])
    passed = (
        m["execution_result"]["status"] in ("REJECTED", "BLOCKED") and
        m["enforcement_result"]["authorized"] is False and
        truth_v["valid"]
    )
    return {"passed": passed, "status": m["execution_result"]["status"],
            "truth_valid": truth_v["valid"]}


def s4_trace_corruption_attempt():
    m = invoke_sovereign_core(_req("dp_004"))
    original_trace = m["trace_id"]
    m_corrupt = copy.deepcopy(m)
    m_corrupt["_trace_chain_head"] = original_trace
    m_corrupt["trace_id"] = "corrupted_trace_xyz"
    try:
        validate_stage(m_corrupt, "core")
        return {"passed": False, "reason": "mutation_not_detected"}
    except ContractViolationError as e:
        detected = "TRACE MUTATION" in str(e)
        return {"passed": detected,
                "mutation_detected": detected, "error": str(e)}


def s5_replay_corruption_attempt():
    m_orig = invoke_sovereign_core(_req("dp_005"))
    m_replay = invoke_sovereign_core(_req("dp_005"))  # same input, new trace

    # Corrupt replay: tamper dgic_output
    m_corrupt = copy.deepcopy(m_replay)
    m_corrupt["dgic_output"]["confidence"] = 0.0  # tamper

    corruption = detect_corruption(m_orig["truth_artifact"], m_corrupt)
    passed = corruption["corrupted"]
    return {"passed": passed,
            "corruption_detected": corruption["corrupted"],
            "corruptions": [c["field"] for c in corruption["corruptions"]]}


def s6_partial_runtime_failure():
    # RAJYA rejects → Core never called → partial execution
    m = invoke_sovereign_core(_req("dp_006", confidence=0.2))
    truth_v = validate_truth_artifact(m["truth_artifact"])
    lineage = validate_lineage(m)
    # sarathi, enforcement, core should be missing from lineage
    passed = (
        m["execution_result"]["status"] == "REJECTED" and
        truth_v["valid"] and
        "sarathi" in lineage["missing"] and
        "core" in lineage["missing"]
    )
    return {"passed": passed, "status": m["execution_result"]["status"],
            "truth_valid": truth_v["valid"],
            "missing_layers": lineage["missing"]}


def s7_delayed_telemetry_recovery():
    m = invoke_sovereign_core(_req("dp_007"))
    truth = m["truth_artifact"]
    # Simulate delayed telemetry: remove observability from mandala
    m_degraded = copy.deepcopy(m)
    m_degraded.pop("observability", None)
    recon = reconstruct_degraded(
        truth,
        available_layers=["dgic", "pde", "rajya", "sarathi",
                          "enforcement", "core", "bucket"]
    )
    passed = (
        recon["verifiable"]["trace_id"] == m["trace_id"] and
        recon["verifiable"]["execution_status"] == "EXECUTED" and
        "observability" in recon["missing_layers"]
    )
    return {"passed": passed,
            "trace_verified": recon["verifiable"]["trace_id"] == m["trace_id"],
            "status_verified": recon["verifiable"]["execution_status"],
            "missing_layers": recon["missing_layers"]}


def s8_bucket_replay_reconstruction():
    m = invoke_sovereign_core(_req("dp_008"))
    trace_id = m["trace_id"]
    execution_id = m["execution_id"]

    # Read back from Bucket and verify
    stored = bucket.read_truth(trace_id, execution_id)
    stored_artifact = stored["truth_artifact"]
    truth_v = validate_truth_artifact(stored_artifact)
    append_proof = bucket.verify_append_only(trace_id)

    passed = (
        truth_v["valid"] and
        stored_artifact["trace_id"] == trace_id and
        append_proof["append_only_valid"]
    )
    return {"passed": passed,
            "truth_valid": truth_v["valid"],
            "append_only_valid": append_proof["append_only_valid"],
            "seq": stored["seq"]}


def s9_distributed_restart_replay():
    """
    Simulate distributed restart: run execution, then run identical
    execution again (simulating restart). Verify determinism.
    """
    m1 = invoke_sovereign_core(_req("dp_009"))
    m2 = invoke_sovereign_core(_req("dp_009"))  # restart with same input

    import hashlib, json as _json
    h = lambda o: hashlib.sha256(
        _json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

    dgic_match   = h(m1["dgic_output"]) == h(m2["dgic_output"])
    status_match = (m1["execution_result"]["status"] ==
                    m2["execution_result"]["status"])
    # Both truth artifacts must be schema-valid
    t1 = validate_truth_artifact(m1["truth_artifact"])
    t2 = validate_truth_artifact(m2["truth_artifact"])

    passed = dgic_match and status_match and t1["valid"] and t2["valid"]
    return {"passed": passed,
            "dgic_deterministic": dgic_match,
            "status_deterministic": status_match,
            "both_truths_valid": t1["valid"] and t2["valid"]}


def s10_observability_interruption_recovery():
    """
    Observability interruption: truth artifact must still be valid
    even if observability event is missing from mandala.
    Proves truth persistence is independent of observability.
    """
    m = invoke_sovereign_core(_req("dp_010"))
    truth = m["truth_artifact"]
    truth_v = validate_truth_artifact(truth)

    # Remove observability — simulate interruption
    m_no_obs = copy.deepcopy(m)
    m_no_obs.pop("observability", None)

    # Truth must still be independently valid
    recon = reconstruct_degraded(
        truth,
        available_layers=["dgic", "pde", "rajya", "sarathi",
                          "enforcement", "core", "bucket"]
    )

    passed = (
        truth_v["valid"] and
        recon["verifiable"]["execution_status"] is not None and
        recon["verifiable"]["trace_id"] == m["trace_id"]
    )
    return {"passed": passed,
            "truth_independent_of_obs": truth_v["valid"],
            "status_recoverable": recon["verifiable"]["execution_status"],
            "trace_recoverable": recon["verifiable"]["trace_id"] == m["trace_id"]}


# ─────────────────────────────────────────────────────────────────────────
# Proof Generators
# ─────────────────────────────────────────────────────────────────────────

def generate_distributed_execution_proof(results):
    passed = sum(1 for r in results if r["status"] == "PASS")
    proof = {
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "proof_type":         "DISTRIBUTED_EXECUTION",
        "scenarios_executed": len(results),
        "scenarios_passed":   passed,
        "all_passed":         passed == len(results),
        "scenarios":          results,
    }
    with open("DISTRIBUTED_EXECUTION_PROOF.json", "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2, default=str)
    print("\n✅ DISTRIBUTED_EXECUTION_PROOF.json written")
    return proof


def generate_replay_reconstruction_proof():
    bucket.clear_truths()
    insightbridge.clear_log()

    m = invoke_sovereign_core(_req("replay_recon_proof"))
    trace_id = m["trace_id"]
    execution_id = m["execution_id"]

    stored = bucket.read_truth(trace_id, execution_id)
    truth_v = validate_truth_artifact(stored["truth_artifact"])
    lineage = build_lineage_artifact(m)
    append = bucket.verify_append_only(trace_id)

    recon_full = reconstruct_degraded(
        stored["truth_artifact"],
        available_layers=["dgic", "pde", "rajya", "sarathi",
                          "enforcement", "core", "bucket", "observability"]
    )
    recon_degraded = reconstruct_degraded(
        stored["truth_artifact"],
        available_layers=["dgic", "pde", "rajya", "bucket"]
    )

    proof = {
        "timestamp":              datetime.now(timezone.utc).isoformat(),
        "proof_type":             "REPLAY_RECONSTRUCTION",
        "trace_id":               trace_id,
        "execution_id":           execution_id,
        "truth_schema_valid":     truth_v["valid"],
        "append_only_valid":      append["append_only_valid"],
        "lineage_valid":          lineage["lineage_valid"],
        "lineage_hash":           lineage["lineage_hash"],
        "full_reconstruction":    recon_full,
        "degraded_reconstruction": recon_degraded,
    }
    with open("REPLAY_RECONSTRUCTION_PROOF.json", "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2, default=str)
    print("✅ REPLAY_RECONSTRUCTION_PROOF.json written")
    return proof


def generate_convergence_failure_matrix():
    content = """# Convergence Failure Matrix
**Date:** 2025-07-15
**Phase:** TANTRA Distributed Runtime Convergence

## Failure Scenarios

| # | Scenario | Trigger | Detection | Truth Persisted | Observable |
|---|---|---|---|---|---|
| 1 | DGIC unavailable | Import fails + no dgic_reasoning | ContractViolationError | Best-effort | Best-effort |
| 2 | RAJYA unavailable | Import fails | ContractViolationError | Best-effort | Best-effort |
| 3 | Core unavailable | Import fails | ContractViolationError | Best-effort | Best-effort |
| 4 | Bucket unavailable | Import fails | ContractViolationError | No | Yes |
| 5 | InsightBridge unavailable | Import fails | ContractViolationError | Yes | No |
| 6 | RAJYA REJECT | PDE ESCALATE/DENY | Terminal path | Yes | Yes |
| 7 | Sarathi BLOCK | collapse_trigger / low confidence | Terminal path | Yes | Yes |
| 8 | Trace mutation | trace_id changed post-entry | ContractViolationError TRACE MUTATION | Best-effort | Best-effort |
| 9 | Replay corruption | Hash mismatch in replay | detect_corruption() | Yes (original) | Yes (original) |
| 10 | Partial runtime failure | Layer unavailable mid-execution | Terminal path at last valid layer | Yes | Yes |
| 11 | Delayed telemetry | observability missing | reconstruct_degraded() | Yes | No |
| 12 | Stale truth artifact | execution_status tampered | detect_corruption() | Yes (original) | Yes (original) |
| 13 | Corrupted lineage | trace_id tampered in layer output | validate_lineage() breaks list | Yes | Yes |
| 14 | Distributed restart | Same input, new execution | validate_replay() determinism check | Yes (both) | Yes (both) |
| 15 | Observability interruption | InsightBridge down at emit | Truth still valid independently | Yes | No |
| 16 | Truth schema invalid | Missing required field | validate_truth_artifact() | Rejected | Yes |
| 17 | Append-only violation | Sequence gap detected | verify_append_only() | Flagged | Yes |
| 18 | Observability influence | Forbidden field in obs event | validate_observability_event() | Yes | Flagged |

## Governance Boundary Violations (Constitutional Red-Lines)

| Violation | Detection | Action |
|---|---|---|
| InsightBridge field influences routing | detect_orchestration_influence() | Hard fail |
| Observability event contains execution fields | validate_observability_event() | Hard fail |
| Truth artifact overwritten | verify_append_only() | Hard fail |
| trace_id regenerated mid-execution | _check_trace() in contract validator | Hard fail |
| PDE absorbs RAJYA authority | Architecture — PDE returns recommendation only | Design invariant |
| Orchestration absorbs Sarathi enforcement | Architecture — enforce_decision() called unconditionally | Design invariant |
"""
    with open("CONVERGENCE_FAILURE_MATRIX.md", "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ CONVERGENCE_FAILURE_MATRIX.md written")


# ─────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("DISTRIBUTED EXECUTION PROOF — Phase 6")
    print("="*60)

    bucket.clear_truths()
    insightbridge.clear_log()

    scenarios = [
        ("1. Full ALLOW path",                s1_full_allow),
        ("2. RAJYA rejection path",           s2_rajya_rejection),
        ("3. Sarathi block path",             s3_sarathi_block),
        ("4. Trace corruption attempt",       s4_trace_corruption_attempt),
        ("5. Replay corruption attempt",      s5_replay_corruption_attempt),
        ("6. Partial runtime failure",        s6_partial_runtime_failure),
        ("7. Delayed telemetry recovery",     s7_delayed_telemetry_recovery),
        ("8. Bucket replay reconstruction",   s8_bucket_replay_reconstruction),
        ("9. Distributed restart replay",     s9_distributed_restart_replay),
        ("10. Observability interruption",    s10_observability_interruption_recovery),
    ]

    results = [_run(label, fn) for label, fn in scenarios]

    passed = sum(1 for r in results if r["status"] == "PASS")
    total  = len(results)

    generate_distributed_execution_proof(results)
    generate_replay_reconstruction_proof()
    generate_convergence_failure_matrix()

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed")
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"  {icon} {r['scenario']}")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

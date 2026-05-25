"""
sovereign_core_entry.py
SOVEREIGN CORE CONVERGENCE — Real Integration Layer

Single entry point: invoke_sovereign_core(request)
Strict flow: validate → trace_id → DGIC → PDE → RAJYA → Sarathi → Enforcement → Core → Bucket → Observability → return

CRITICAL REQUIREMENTS:
- Canonical trace_id generated ONCE at entry, immutable throughout
- NO fallback stubs — hard fail if modules unavailable
- Bucket write MANDATORY for all terminal paths
- Telemetry MANDATORY for all terminal paths
- Every execution produces replay-safe truth artifact
- No trace mutation, no hidden remapping
"""

from datetime import datetime, timezone
import uuid
import json
import hashlib
from typing import Optional

from pde_engine import evaluate as pde_evaluate
from pde_contract import compute_hash as pde_compute_hash
from sarathi_engine import evaluate as sarathi_evaluate
from enforcement import enforce_decision
from decision_contract import compute_hash as sarathi_compute_hash
from truth_contracts import build_truth_artifact
from execution_contract_validator import (
    ContractViolationError,
    validate_input_contract,
    validate_stage,
    validate_no_mutation,
)

# ─────────────────────────────────────────────────────────────────────────
# REAL MODULE IMPORTS — Hard fail if unavailable (PHASE 1)
# ─────────────────────────────────────────────────────────────────────────

_DGIC_AVAILABLE = False
_RAJYA_AVAILABLE = False
_CORE_AVAILABLE = False
_BUCKET_AVAILABLE = False
_INSIGHTBRIDGE_AVAILABLE = False

try:
    import dgic  # type: ignore
    _DGIC_AVAILABLE = True
except ImportError:
    pass

try:
    import rajya  # type: ignore
    _RAJYA_AVAILABLE = True
except ImportError:
    pass

try:
    import core  # type: ignore
    _CORE_AVAILABLE = True
except ImportError:
    pass

try:
    import bucket  # type: ignore
    _BUCKET_AVAILABLE = True
except ImportError:
    pass

try:
    import insightbridge  # type: ignore
    _INSIGHTBRIDGE_AVAILABLE = True
except ImportError:
    pass


# ─────────────────────────────────────────────────────────────────────────
# TRACE CONTINUITY LOCK (PHASE 2)
# ─────────────────────────────────────────────────────────────────────────

def _generate_canonical_trace_id() -> str:
    """Generate canonical trace_id ONCE at entry point."""
    return f"trace_{uuid.uuid4().hex[:16]}"


def _compute_trace_hash(trace_id: str, execution_state: dict) -> str:
    """Compute immutable trace hash for verification."""
    state_str = json.dumps(execution_state, sort_keys=True, default=str)
    combined = f"{trace_id}:{state_str}"
    return hashlib.sha256(combined.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────
# DGIC INTERFACE — Real module or hard fail
# ─────────────────────────────────────────────────────────────────────────

def _call_dgic(trace_id: str, execution_id: str, ksml_input: dict) -> dict:
    """
    Call DGIC (Pritesh Patra) with trace propagation.
    
    PHASE 1 REQUIREMENT: No fallback stubs.
    If DGIC not available and no pre-computed dgic_reasoning:
    → HARD FAIL
    """
    if _DGIC_AVAILABLE:
        # trace_id NOT injected into dgic_reasoning — pde_contract enforces strict key match
        return dgic.analyze(execution_id, ksml_input)

    # Harness/test path: embedded dgic_reasoning passed through as-is
    if "dgic_reasoning" in ksml_input:
        return ksml_input["dgic_reasoning"]

    # HARD FAIL
    raise ContractViolationError(
        f"[{trace_id}] DGIC module unavailable (import failed) "
        "and no dgic_reasoning in ksml_input. "
        "PHASE 1 REQUIREMENT: Real module or explicit hard fail."
    )


# ─────────────────────────────────────────────────────────────────────────
# RAJYA INTERFACE — Real module or hard fail
# ─────────────────────────────────────────────────────────────────────────

def _call_rajya(trace_id: str, execution_id: str, policy_decision: dict) -> dict:
    """
    Call RAJYA (Rajaryan Verma) with trace propagation.
    
    PHASE 1 REQUIREMENT: No fallback stubs.
    If RAJYA not available: → HARD FAIL
    """
    if _RAJYA_AVAILABLE:
        rajya_output = rajya.validate(execution_id, policy_decision)
        rajya_output["trace_id"] = trace_id  # Propagate trace
        return rajya_output

    # HARD FAIL: No RAJYA module
    raise ContractViolationError(
        f"[{trace_id}] RAJYA module unavailable (import failed). "
        "PHASE 1 REQUIREMENT: Real module or explicit hard fail."
    )


# ─────────────────────────────────────────────────────────────────────────
# CORE INTERFACE — Real module or hard fail
# ─────────────────────────────────────────────────────────────────────────

def _call_core(trace_id: str, execution_id: str, sarathi_token: dict) -> dict:
    """
    Call Core (Raj Prajapati) with trace propagation.
    
    PHASE 1 REQUIREMENT: No fallback stubs.
    If Core not available: → HARD FAIL
    """
    if _CORE_AVAILABLE:
        core_output = core.execute(execution_id, sarathi_token)
        core_output["trace_id"] = trace_id  # Propagate trace
        return core_output

    # HARD FAIL: No Core module
    raise ContractViolationError(
        f"[{trace_id}] Core module unavailable (import failed). "
        "PHASE 1 REQUIREMENT: Real module or explicit hard fail."
    )


# ─────────────────────────────────────────────────────────────────────────
# BUCKET TRUTH LAYER INTEGRATION (PHASE 3)
# ─────────────────────────────────────────────────────────────────────────

def _emit_truth_artifact(trace_id: str, mandala: dict) -> dict:
    """
    Build schema v2 truth artifact and persist to Bucket.
    PHASE 4: Uses truth_contracts.build_truth_artifact (schema v2).
    Bucket is append-only — no overwrite.
    """
    # Build lineage hash for inclusion in truth artifact
    try:
        from distributed_trace_federation import build_lineage_artifact
        lineage = build_lineage_artifact(mandala)
        lineage_hash = lineage["lineage_hash"]
    except Exception:
        lineage_hash = None

    truth_artifact = build_truth_artifact(trace_id, mandala, lineage_hash=lineage_hash)

    execution_id = mandala.get("execution_id", "unknown")

    if _BUCKET_AVAILABLE:
        try:
            bucket.write_truth(trace_id, execution_id, truth_artifact)
        except Exception as e:
            raise ContractViolationError(
                f"[{trace_id}] Bucket write failed (PHASE 3 REQUIREMENT VIOLATED): {e}"
            )
    else:
        raise ContractViolationError(
            f"[{trace_id}] Bucket module unavailable. "
            "PHASE 3 REQUIREMENT: Truth persistence is MANDATORY."
        )

    return truth_artifact


# ─────────────────────────────────────────────────────────────────────────
# MANDATORY OBSERVABILITY FLOW (PHASE 4)
# ─────────────────────────────────────────────────────────────────────────

def _emit_observability(trace_id: str, mandala: dict, truth_artifact: dict) -> dict:
    """
    Emit deterministic observability event.
    
    PHASE 4 REQUIREMENT: Telemetry is MANDATORY, not optional.
    Every terminal path must emit observability.
    """
    execution_id = mandala.get("execution_id", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    observability_event = {
        "trace_id": trace_id,
        "execution_id": execution_id,
        "timestamp": timestamp,
        "dgic_decision": mandala.get("dgic_output", {}).get("decision", "UNKNOWN"),
        "pde_decision": mandala.get("policy_decision", {}).get("policy_decision", {}).get("decision", "UNKNOWN"),
        "rajya_verdict": mandala.get("rajya_verdict", {}).get("verdict", "UNKNOWN"),
        "sarathi_decision": mandala.get("sarathi_token", {}).get("decision", "UNKNOWN"),
        "enforcement_authorized": mandala.get("enforcement_result", {}).get("authorized", False),
        "execution_status": mandala.get("execution_result", {}).get("status", "UNKNOWN"),
        "failure_reason": mandala.get("execution_result", {}).get("reason", None),
        "truth_artifact_trace": truth_artifact.get("trace_id"),
        "contract_version": "1.0",
    }
    
    # Emit to InsightBridge if available
    if _INSIGHTBRIDGE_AVAILABLE:
        try:
            insightbridge.emit(observability_event)
        except Exception as e:
            raise ContractViolationError(
                f"[{trace_id}] InsightBridge emission failed: {e}"
            )
    else:
        raise ContractViolationError(
            f"[{trace_id}] InsightBridge module unavailable. "
            "PHASE 4 REQUIREMENT: Observability emission is MANDATORY."
        )
    
    return observability_event


def invoke_sovereign_core(request: dict) -> dict:
    """
    CONVERGENCE ENTRY POINT — Real Sovereign Core Execution.
    
    Single entry point for the Sovereign Core.
    Canonical trace_id generated ONCE at entry, propagated immutably through:
    DGIC → PDE → RAJYA → Sarathi → Enforcement → Core → Bucket → InsightBridge
    
    MANDATORY REQUIREMENTS:
    - trace_id never regenerated or mutated
    - Bucket write required for all terminal paths
    - Observability emission required for all terminal paths
    - Hard fail if modules unavailable (PHASE 1)
    - Replay-safe truth artifacts (PHASE 3)
    - Mandatory telemetry (PHASE 4)
    
    Args:
        request: {
            "execution_id": str,
            "ksml_input": dict   (may carry dgic_reasoning for test/harness)
        }

    Returns:
        Mandala Object with trace_id, all layer outputs, truth_artifact, and observability.
    
    Raises:
        ContractViolationError: If modules unavailable or requirements violated.
    """
    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2: Generate canonical trace_id ONCE at entry
    # ─────────────────────────────────────────────────────────────────────────
    trace_id = _generate_canonical_trace_id()
    
    # Initialize mandala with trace_id
    mandala = dict(request)
    mandala["trace_id"] = trace_id
    mandala["_trace_chain_head"] = trace_id  # For verification
    
    execution_id = None
    
    try:
        # ──────────────────────────────────────────────────────────────────
        # Step 1: Validate input contract
        # ──────────────────────────────────────────────────────────────────
        validate_input_contract(mandala)
        execution_id = mandala["execution_id"]
        
        print(f"[{trace_id}] ✓ Input validated: execution_id={execution_id}")

        # ──────────────────────────────────────────────────────────────────
        # Step 2: Call DGIC (with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        dgic_reasoning = _call_dgic(trace_id, execution_id, mandala["ksml_input"])
        # trace_id is stored on mandala only — never injected into dgic_reasoning
        # (pde_contract enforces strict key match on dgic_reasoning)
        mandala["dgic_output"] = dgic_reasoning
        validate_stage(mandala, "dgic")
        
        print(f"[{trace_id}] ✓ DGIC: decision={dgic_reasoning.get('decision')}")

        # ──────────────────────────────────────────────────────────────────
        # Step 3: Call PDE (with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        # PDE contract expects exactly {execution_id, dgic_reasoning} — no extra keys
        pde_payload = {
            "execution_id": execution_id,
            "dgic_reasoning": dgic_reasoning,
        }
        policy_decision = pde_evaluate(pde_payload)
        policy_decision["trace_id"] = trace_id  # attach trace to PDE output
        mandala["policy_decision"] = policy_decision
        validate_stage(mandala, "pde")
        validate_no_mutation({"dgic_output": dgic_reasoning}, mandala, ["dgic_output"], "pde")
        
        print(f"[{trace_id}] ✓ PDE: decision={policy_decision.get('policy_decision', {}).get('decision')}")

        # ──────────────────────────────────────────────────────────────────
        # Step 4: Call RAJYA (with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        rajya_verdict = _call_rajya(trace_id, execution_id, policy_decision)
        mandala["rajya_verdict"] = rajya_verdict
        validate_stage(mandala, "rajya")
        
        print(f"[{trace_id}] ✓ RAJYA: verdict={rajya_verdict.get('verdict')}")

        # ──────────────────────────────────────────────────────────────────
        # Step 5: RAJYA REJECT → Terminal Path (PHASE 3 + 4)
        # ──────────────────────────────────────────────────────────────────
        if rajya_verdict.get("verdict") != "APPROVED":
            mandala["enforcement_result"] = {"authorized": False}
            mandala["execution_result"] = {
                "execution_id": execution_id,
                "status": "REJECTED",
                "reason": rajya_verdict.get("reason", "rajya_reject"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            }
            
            print(f"[{trace_id}] ⊘ RAJYA rejected: {rajya_verdict.get('reason')}")
            
            # PHASE 3: Emit truth artifact
            truth_artifact = _emit_truth_artifact(trace_id, mandala)
            mandala["truth_artifact"] = truth_artifact
            print(f"[{trace_id}] ✓ Truth artifact persisted to Bucket")
            
            # PHASE 4: Emit observability
            observability = _emit_observability(trace_id, mandala, truth_artifact)
            mandala["observability"] = observability
            print(f"[{trace_id}] ✓ Observability emitted to InsightBridge")
            
            return mandala

        # ──────────────────────────────────────────────────────────────────
        # Step 6: Call Sarathi (token mint, with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        dgic_output_for_sarathi = {
            "confidence":       dgic_reasoning.get("confidence", 0.0),
            "epistemic_state":  dgic_reasoning.get("epistemic_state", "unknown"),
            "collapse_trigger": dgic_reasoning.get("collapse_trigger", False),
        }
        # Sarathi decision_contract enforces strict key match:
        # {execution_id, dgic_output, execution_hash, timestamp} — no extra keys
        sarathi_payload = {
            "execution_id":   execution_id,
            "dgic_output":    dgic_output_for_sarathi,
            "execution_hash": sarathi_compute_hash(execution_id, dgic_output_for_sarathi),
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        sarathi_token = sarathi_evaluate(sarathi_payload)
        sarathi_token["trace_id"] = trace_id  # propagate trace into token
        mandala["sarathi_token"] = sarathi_token
        mandala["trace_id"] = trace_id  # ensure mandala trace_id never drifts
        validate_stage(mandala, "sarathi")
        
        print(f"[{trace_id}] ✓ Sarathi: decision={sarathi_token.get('decision')}")

        # ──────────────────────────────────────────────────────────────────
        # Step 7: Enforce (non-bypassable gate, with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        authorized = enforce_decision(execution_id, sarathi_token)
        mandala["enforcement_result"] = {"authorized": authorized, "trace_id": trace_id}
        mandala["trace_id"] = trace_id  # ensure mandala trace_id never drifts
        validate_stage(mandala, "enforcement")

        if not authorized:
            mandala["execution_result"] = {
                "execution_id": execution_id,
                "status": "BLOCKED",
                "reason": sarathi_token.get("reason", "enforcement_denied"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            }
            
            print(f"[{trace_id}] ⊘ Enforcement blocked: {sarathi_token.get('reason')}")
            
            # PHASE 3: Emit truth artifact
            truth_artifact = _emit_truth_artifact(trace_id, mandala)
            mandala["truth_artifact"] = truth_artifact
            print(f"[{trace_id}] ✓ Truth artifact persisted to Bucket")
            
            # PHASE 4: Emit observability
            observability = _emit_observability(trace_id, mandala, truth_artifact)
            mandala["observability"] = observability
            print(f"[{trace_id}] ✓ Observability emitted to InsightBridge")
            
            return mandala

        # ──────────────────────────────────────────────────────────────────
        # Step 8: Call Core (with trace propagation)
        # ──────────────────────────────────────────────────────────────────
        execution_result = _call_core(trace_id, execution_id, sarathi_token)
        mandala["execution_result"] = execution_result
        validate_stage(mandala, "core")
        
        print(f"[{trace_id}] ✓ Core: status={execution_result.get('status')}")

        # ──────────────────────────────────────────────────────────────────
        # Step 9: PHASE 3 - Emit truth artifact to Bucket (MANDATORY)
        # ──────────────────────────────────────────────────────────────────
        truth_artifact = _emit_truth_artifact(trace_id, mandala)
        mandala["truth_artifact"] = truth_artifact
        print(f"[{trace_id}] ✓ Truth artifact persisted to Bucket")

        # ──────────────────────────────────────────────────────────────────
        # Step 10: PHASE 4 - Emit observability to InsightBridge (MANDATORY)
        # ──────────────────────────────────────────────────────────────────
        observability = _emit_observability(trace_id, mandala, truth_artifact)
        mandala["observability"] = observability
        print(f"[{trace_id}] ✓ Observability emitted to InsightBridge")

        # ──────────────────────────────────────────────────────────────────
        # Step 11: Return complete mandala
        # ──────────────────────────────────────────────────────────────────
        print(f"[{trace_id}] ✅ EXECUTION COMPLETE")
        return mandala

    except ContractViolationError as e:
        # ──────────────────────────────────────────────────────────────────
        # Handle contract violations
        # ──────────────────────────────────────────────────────────────────
        print(f"[{trace_id}] ❌ CONTRACT VIOLATION: {e}")
        
        mandala["error"] = str(e)
        if execution_id:
            mandala["execution_result"] = {
                "execution_id": execution_id,
                "status": "FAILED",
                "reason": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            }
        
        # Still try to emit truth + observability if possible
        try:
            truth_artifact = _emit_truth_artifact(trace_id, mandala)
            mandala["truth_artifact"] = truth_artifact
            observability = _emit_observability(trace_id, mandala, truth_artifact)
            mandala["observability"] = observability
        except:
            pass  # Best effort — don't mask original error
        
        raise


"""
Enforcement Layer - Validates execution readiness before Core proceeds
Requirement #7: Non-bypassable decision enforcement
"""

from sarathi_engine import evaluate


def enforce_decision(execution_id: str, sarathi_decision: dict) -> bool:
    """
    Validates that a decision token is valid before Core proceeds.
    
    Args:
        execution_id: Must match decision token execution_id
        sarathi_decision: Decision dict from Sarathi.evaluate()
    
    Returns:
        bool: True if execution can proceed, False otherwise
    
    Rules:
        - execution_id must match decision token
        - decision must be "ALLOW" (not DENY or ESCALATE)
        - decision must have valid timestamp
    """
    if not sarathi_decision:
        print(f"❌ REJECT {execution_id}: No decision token provided")
        return False
    
    if sarathi_decision["execution_id"] != execution_id:
        print(f"❌ REJECT {execution_id}: execution_id mismatch in token")
        return False
    
    if sarathi_decision["decision"] != "ALLOW":
        print(f"❌ REJECT {execution_id}: Decision is {sarathi_decision['decision']}, not ALLOW")
        return False
    
    if not sarathi_decision.get("timestamp"):
        print(f"❌ REJECT {execution_id}: Decision has no timestamp")
        return False
    
    print(f"✅ ALLOW {execution_id}: Decision enforced successfully")
    return True


def core_gate(execution_id: str, payload: dict, policy_path: str = None) -> dict:
    """
    Complete gate: Sarathi decision → Enforcement → Ready for Core
    
    Flow:
        1. Call Sarathi.evaluate(payload)
        2. Enforce decision token
        3. Return execution readiness
    
    Args:
        execution_id: Request ID
        payload: Input contract dict
        policy_path: Optional custom policy file
    
    Returns:
        dict: {
            "execution_id": str,
            "authorized": bool,
            "decision": dict,
            "reason": str
        }
    """
    # Step 1: Get Sarathi decision
    decision = evaluate(payload, policy_path)
    
    # Step 2: Enforce it
    authorized = enforce_decision(execution_id, decision)
    
    # Step 3: Return readiness gate
    return {
        "execution_id": execution_id,
        "authorized": authorized,
        "decision": decision,
        "reason": "execution_ready" if authorized else "execution_denied"
    }

import json
import os

REQUIRED_POLICY_KEYS = {"version", "confidence_threshold", "deny_conditions", "escalation_conditions", "allow_conditions"}

def load_policies(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "policies.json")

    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        policies = json.load(f)

    if not REQUIRED_POLICY_KEYS.issubset(policies.keys()):
        return None

    return policies

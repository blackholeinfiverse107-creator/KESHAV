import json
import hashlib
import copy

def canonical_hash(data) -> str:
    """Returns a deterministic SHA-256 hash of the input data."""
    encoded = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()

def ensure_immutable(original, after_execution):
    """Checks if the original input was mutated."""
    return canonical_hash(original) == canonical_hash(after_execution)

def safe_copy(data):
    """Returns a deep copy of the data."""
    return copy.deepcopy(data)

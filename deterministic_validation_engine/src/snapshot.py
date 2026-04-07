"""
snapshot.py — Phase 1: Input Snapshot System
=============================================
Creates deep, immutable snapshots of pipeline inputs.
Guarantees that validation never mutates the original data.
Produces a deterministic content hash for identity comparison.
"""

import copy
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional


class PipelineSnapshot:
    """
    An immutable, hash-sealed snapshot of a full pipeline input.

    Once created, the snapshot cannot be mutated. The content_hash
    uniquely identifies the exact data — any change in input will
    produce a different hash.
    """

    __slots__ = (
        "_execution_id",
        "_tasks",
        "_constraint_results",
        "_propagation_results",
        "_bottleneck_output",
        "_content_hash",
        "_snapshot_id",
    )

    def __init__(
        self,
        execution_id: str,
        tasks: List[dict],
        constraint_results: List[dict],
        propagation_results: List[dict],
        bottleneck_output: dict,
    ):
        # Deep copy everything to guarantee immutability
        self._execution_id = str(execution_id)
        self._tasks = copy.deepcopy(tasks)
        self._constraint_results = copy.deepcopy(constraint_results)
        self._propagation_results = copy.deepcopy(propagation_results)
        self._bottleneck_output = copy.deepcopy(bottleneck_output)
        self._snapshot_id = str(uuid.uuid4())

        # Compute deterministic content hash
        self._content_hash = self._compute_hash()

    # ------------------------------------------------------------------
    # Public accessors (return deep copies to prevent mutation)
    # ------------------------------------------------------------------

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    @property
    def tasks(self) -> List[dict]:
        return copy.deepcopy(self._tasks)

    @property
    def constraint_results(self) -> List[dict]:
        return copy.deepcopy(self._constraint_results)

    @property
    def propagation_results(self) -> List[dict]:
        return copy.deepcopy(self._propagation_results)

    @property
    def bottleneck_output(self) -> dict:
        return copy.deepcopy(self._bottleneck_output)

    @property
    def content_hash(self) -> str:
        return self._content_hash

    # ------------------------------------------------------------------
    # Reconstruction: returns the full input as a plain dict
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Reconstruct the original pipeline input from this snapshot."""
        return {
            "execution_id": self._execution_id,
            "tasks": copy.deepcopy(self._tasks),
            "constraint_results": copy.deepcopy(self._constraint_results),
            "propagation_results": copy.deepcopy(self._propagation_results),
            "bottleneck_output": copy.deepcopy(self._bottleneck_output),
        }

    # ------------------------------------------------------------------
    # Hash computation (deterministic, canonical JSON)
    # ------------------------------------------------------------------

    def _compute_hash(self) -> str:
        """
        Produces a SHA-256 hash of the canonical JSON representation.
        Keys are sorted, floats are rounded to 12 decimal places to
        avoid platform-dependent floating-point representation issues.
        """
        canonical = self._canonical_json(self.to_dict())
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_json(obj: Any) -> str:
        """
        Produce a canonical, deterministic JSON string.
        - dict keys are sorted
        - floats are rounded to 12 decimal places
        - no whitespace beyond separators
        """
        return json.dumps(obj, sort_keys=True, default=_json_default, separators=(",", ":"))

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def matches(self, other: "PipelineSnapshot") -> bool:
        """Returns True if two snapshots have identical content."""
        return self._content_hash == other._content_hash

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PipelineSnapshot):
            return NotImplemented
        return self._content_hash == other._content_hash

    def __hash__(self) -> int:
        return hash(self._content_hash)

    def __repr__(self) -> str:
        return (
            f"PipelineSnapshot(execution_id={self._execution_id!r}, "
            f"hash={self._content_hash[:16]}..., "
            f"tasks={len(self._tasks)}, "
            f"constraints={len(self._constraint_results)}, "
            f"propagations={len(self._propagation_results)})"
        )


# ----------------------------------------------------------------------
# Helper for canonical JSON serialization
# ----------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """Handle non-standard types in JSON serialization."""
    if isinstance(obj, float):
        return round(obj, 12)
    if isinstance(obj, complex):
        return {"__complex__": True, "real": round(obj.real, 12), "imag": round(obj.imag, 12)}
    if isinstance(obj, set):
        return sorted(list(obj))
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ----------------------------------------------------------------------
# Factory function
# ----------------------------------------------------------------------

def create_snapshot(pipeline_input: dict) -> PipelineSnapshot:
    """
    Factory: create a PipelineSnapshot from a raw pipeline input dict.
    Validates required keys before construction.
    """
    required_keys = {"execution_id", "tasks", "constraint_results", "propagation_results", "bottleneck_output"}
    missing = required_keys - set(pipeline_input.keys())
    if missing:
        raise ValueError(f"Pipeline input missing required keys: {missing}")

    return PipelineSnapshot(
        execution_id=pipeline_input["execution_id"],
        tasks=pipeline_input["tasks"],
        constraint_results=pipeline_input["constraint_results"],
        propagation_results=pipeline_input["propagation_results"],
        bottleneck_output=pipeline_input["bottleneck_output"],
    )

"""
health.py — KESHAV-4 Propagation Engine Health Check
=====================================================
Validates:
  1. Python environment readiness
  2. Pydantic dependency availability
  3. Schema registry import chain integrity
  4. PropagationEngine instantiation and execution
  5. Contract violation handling
  6. Deterministic BFS output verification

Run: python app/health.py
"""

import sys
import os
import time
import json

# Ensure repo root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
KESHAV4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if KESHAV4_ROOT not in sys.path:
    sys.path.insert(0, KESHAV4_ROOT)

CHECKS_PASSED = 0
CHECKS_FAILED = 0
TOTAL_CHECKS = 0

def check(name, fn):
    global CHECKS_PASSED, CHECKS_FAILED, TOTAL_CHECKS
    TOTAL_CHECKS += 1
    start = time.perf_counter()
    try:
        result = fn()
        elapsed = (time.perf_counter() - start) * 1000
        if result:
            CHECKS_PASSED += 1
            print(f"  [PASS] {name} ({elapsed:.1f}ms)")
            return True
        else:
            CHECKS_FAILED += 1
            print(f"  [FAIL] {name} ({elapsed:.1f}ms) — returned False")
            return False
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        CHECKS_FAILED += 1
        print(f"  [FAIL] {name} ({elapsed:.1f}ms) — {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 60)
    print("KESHAV-4 Propagation Engine — Health Check")
    print("=" * 60)
    overall_start = time.perf_counter()

    # 1. Python Environment
    print(f"\n[1/6] Python Environment")
    check("Python version >= 3.10", lambda: sys.version_info >= (3, 10))

    # 2. Pydantic Dependency
    print(f"\n[2/6] Pydantic Dependency")
    def check_pydantic():
        import pydantic
        return hasattr(pydantic, 'BaseModel')
    check("Pydantic importable", check_pydantic)

    # 3. Schema Registry Import Chain
    print(f"\n[3/6] Schema Registry Import Chain")
    def check_registry():
        from shared_canonical_schemas.registry import (
            PropagationInput, PropagationOutput, PropagationContractViolation,
            TantraInputContract, TantraOutputContract, TaskDef,
            ConstraintResult, PropagationResult
        )
        return all([PropagationInput, PropagationOutput, PropagationContractViolation])
    check("shared_canonical_schemas.registry imports", check_registry)

    def check_schemas():
        from shared_schemas.schemas import PropagationInput, PropagationOutput, PropagationContractViolation
        return all([PropagationInput, PropagationOutput, PropagationContractViolation])
    check("shared_schemas.schemas re-exports", check_schemas)

    # 4. Engine Instantiation
    print(f"\n[4/6] PropagationEngine Availability")
    def check_engine():
        from app.engine import PropagationEngine
        return hasattr(PropagationEngine, 'compute_dependency_output') and \
               hasattr(PropagationEngine, 'compute_downstream_path')
    check("PropagationEngine class available", check_engine)

    # 5. Execution Verification
    print(f"\n[5/6] Execution Verification")
    def check_valid_execution():
        from app.engine import PropagationEngine
        input_data = {
            "blocked_task_id": "T1",
            "root_cause": "RC",
            "trace_id": "health-check-trace",
            "timestamp": "2026-05-29T00:00:00Z",
            "dependency_graph": {"RC": ["T1"], "T1": ["T2", "T3"], "T2": ["T4"], "T3": []}
        }
        output = PropagationEngine.compute_dependency_output(input_data)
        assert output["blocked_task_id"] == "T1"
        assert output["root_cause"] == "RC"
        assert output["trace_id"] == "health-check-trace"
        assert output["impacted_tasks"] == ["T2", "T3", "T4"]
        assert output["impact_score"] == 3
        assert output["severity"] == "MEDIUM"
        assert output["resolution_signal"] == "UNBLOCK_DEPENDENCY:RC"
        return True
    check("Valid payload execution", check_valid_execution)

    def check_determinism():
        from app.engine import PropagationEngine
        import random
        graph = {"RC": ["T1"], "T1": ["T3", "T2", "T5", "T4"], "T2": ["T6"], "T3": ["T6"]}
        base_input = {
            "blocked_task_id": "T1", "root_cause": "RC",
            "trace_id": "det-check", "timestamp": "TS",
            "dependency_graph": graph
        }
        ref = json.dumps(PropagationEngine.compute_dependency_output(base_input), sort_keys=True)
        for _ in range(50):
            shuffled = {}
            keys = list(graph.keys())
            random.shuffle(keys)
            for k in keys:
                vals = list(graph[k])
                random.shuffle(vals)
                shuffled[k] = vals
            base_input["dependency_graph"] = shuffled
            current = json.dumps(PropagationEngine.compute_dependency_output(base_input), sort_keys=True)
            assert current == ref, "Determinism check failed!"
        return True
    check("50-iteration determinism proof", check_determinism)

    # 6. Contract Violation Handling
    print(f"\n[6/6] Contract Violation Handling")
    def check_schema_mismatch():
        from app.engine import PropagationEngine
        from shared_schemas.schemas import PropagationContractViolation
        try:
            PropagationEngine.compute_dependency_output({
                "blocked_task_id": "T1", "root_cause": "RC",
                "dependency_graph": {"RC": ["T1"]}
                # Missing trace_id and timestamp
            })
            return False
        except PropagationContractViolation as e:
            return e.code == "SCHEMA_MISMATCH"
    check("Schema mismatch fails closed", check_schema_mismatch)

    def check_broken_root_cause():
        from app.engine import PropagationEngine
        from shared_schemas.schemas import PropagationContractViolation
        try:
            PropagationEngine.compute_dependency_output({
                "blocked_task_id": "T1", "root_cause": "MISSING",
                "trace_id": "t", "timestamp": "ts",
                "dependency_graph": {"T1": ["T2"]}
            })
            return False
        except PropagationContractViolation as e:
            return e.code == "BROKEN_ROOT_CAUSE"
    check("Broken root cause fails closed", check_broken_root_cause)

    def check_invalid_graph():
        from app.engine import PropagationEngine
        from shared_schemas.schemas import PropagationContractViolation
        try:
            PropagationEngine.compute_dependency_output({
                "blocked_task_id": "MISSING_T", "root_cause": "RC",
                "trace_id": "t", "timestamp": "ts",
                "dependency_graph": {"RC": ["T1"]}
            })
            return False
        except PropagationContractViolation as e:
            return e.code == "INVALID_GRAPH"
    check("Invalid graph fails closed", check_invalid_graph)

    # Summary
    overall_elapsed = (time.perf_counter() - overall_start) * 1000
    print(f"\n{'=' * 60}")
    print(f"HEALTH CHECK COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Passed:  {CHECKS_PASSED}/{TOTAL_CHECKS}")
    print(f"  Failed:  {CHECKS_FAILED}/{TOTAL_CHECKS}")
    print(f"  Latency: {overall_elapsed:.1f}ms total")
    print(f"  Status:  {'ALL HEALTHY' if CHECKS_FAILED == 0 else 'DEGRADED'}")
    print(f"{'=' * 60}")

    return CHECKS_FAILED == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

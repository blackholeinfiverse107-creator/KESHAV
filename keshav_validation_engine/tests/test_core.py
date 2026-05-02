import pytest
from src.validator import validate_pipeline
from src.rules import validate_schema

def get_valid_input():
    return {
        "execution_id": "test_exec_1",
        "tasks": [
            {"task_id": "A", "status": "DONE"},
            {"task_id": "B", "status": "PENDING", "depends_on": ["A"]},
            {"task_id": "C", "status": "PENDING", "depends_on": ["B"]}
        ],
        "constraint_results": [
            {"task_id": "B", "is_valid": False, "unsatisfied_dependencies": ["A"]},
            {"task_id": "C", "is_valid": False, "unsatisfied_dependencies": ["B"]}
        ],
        "propagation_results": [
            {"task_id": "B", "affected_tasks": ["C"], "impact_score": 10},
            {"task_id": "C", "affected_tasks": [], "impact_score": 5}
        ],
        "bottleneck_output": {
            "task_id": "B",
            "root_cause": "A",
            "impact_score": 10
        }
    }

def test_phase1_schema():
    data = get_valid_input()
    del data["execution_id"]
    with pytest.raises(ValueError, match="Missing required keys"):
        validate_schema(data)

def test_phase2_constraint_propagation():
    data = get_valid_input()
    # Remove propagation for B
    data["propagation_results"] = data["propagation_results"][1:]
    res = validate_pipeline(data)
    violations = res["violations"]
    assert any(v["type"] == "CONSTRAINT_PROPAGATION_MISMATCH" and v["task_id"] == "B" for v in violations)
    assert not res["consistency_checks"]["constraint_propagation"]

def test_phase3_bottleneck_invalid():
    data = get_valid_input()
    # Make bottleneck point to a non-max impact task
    data["bottleneck_output"]["task_id"] = "C"
    data["bottleneck_output"]["impact_score"] = 5
    res = validate_pipeline(data)
    violations = res["violations"]
    assert any(v["type"] == "BOTTLENECK_INVALID" and v["task_id"] == "C" for v in violations)
    assert not res["consistency_checks"]["propagation_bottleneck"]

def test_phase4_root_cause():
    data = get_valid_input()
    # Root cause not in dependency chain
    data["tasks"].append({"task_id": "X", "status": "DONE"})
    data["bottleneck_output"]["root_cause"] = "X"
    res = validate_pipeline(data)
    violations = res["violations"]
    assert any(v["type"] == "INVALID_ROOT_CAUSE" and v["task_id"] == "X" for v in violations)
    assert not res["consistency_checks"]["root_cause_valid"]

def test_phase5_unsatisfied_dependencies():
    data = get_valid_input()
    # A is marked as DONE, but it's listed as an unsatisfied dependency for B.
    # This should trigger DEPENDENCY_MISMATCH.
    res = validate_pipeline(data)
    violations = res["violations"]
    assert any(v["type"] == "DEPENDENCY_MISMATCH" and v["task_id"] == "B" for v in violations)
    assert not res["consistency_checks"]["dependency_integrity"]



import pytest
from pydantic import ValidationError
from app.engine import PropagationEngine



def test_broken_graph_structure():
    # Phase 4 - Broken graph structure gracefully handled
    input_data = {
        "blocked_task_id": "T1",
        "root_cause": "T1",
        "trace_id": "trace-123",
        "timestamp": "2026-05-02T12:00:00Z",
        "dependency_graph": "INVALID_GRAPH_STRING" # Not a dict
    }
    
    # Engine should sanitize to empty graph and return 0 impact
    output = PropagationEngine.compute_dependency_output(input_data)
    assert output["impact_score"] == 0
    assert output["severity"] == "LOW"
    assert output["impacted_tasks"] == []
    
def test_missing_dependencies():
    # Phase 4 - Handle nodes pointing to non-lists or having missing keys gracefully
    graph = {
        "RC": ["T1", "MISSING_NODE"],
        "T1": "NOT_A_LIST" # invalid value
    }
    input_data = {
        "blocked_task_id": "RC",
        "root_cause": "RC",
        "trace_id": "trace-123",
        "timestamp": "2026-05-02T12:00:00Z",
        "dependency_graph": graph
    }
    # MISSING_NODE should just be added to impacted, and NOT_A_LIST sanitized to []
    output = PropagationEngine.compute_dependency_output(input_data)
    assert "MISSING_NODE" in output["impacted_tasks"]
    assert "T1" in output["impacted_tasks"]
    # impact_score is 2 because MISSING_NODE and T1 are impacted.
    assert output["impact_score"] == 2

def test_root_cause_same_as_blocked():
    graph = {
        "T1": ["T2"]
    }
    input_data = {
        "blocked_task_id": "T1",
        "root_cause": "T1",
        "trace_id": "trace-123",
        "timestamp": "2026-05-02T12:00:00Z",
        "dependency_graph": graph
    }
    # Should succeed because root_cause == blocked_task_id
    output = PropagationEngine.compute_dependency_output(input_data)
    assert output["impacted_tasks"] == ["T2"]

def test_deterministic_bfs_ordering():
    graph = {
        "task_A": ["task_C", "task_B"],
        "task_B": ["task_D", "task_E"],
        "task_C": ["task_E", "task_F"]
    }
    path = PropagationEngine.compute_downstream_path("task_A", graph)
    assert path == ["task_B", "task_C", "task_D", "task_E", "task_F"]

def test_no_duplicates_and_cyclic_handling():
    graph = {
        "task_1": ["task_2", "task_3"],
        "task_2": ["task_4"],
        "task_3": ["task_4"], # task_4 is reachable from 2 and 3
        "task_4": ["task_1"]  # cycle
    }
    path = PropagationEngine.compute_downstream_path("task_1", graph)
    assert path == ["task_2", "task_3", "task_4", "task_1"]

def test_generate_intelligence_schema_compliance():
    graph = {"RC": ["t1"], "t1": ["t2"]}
    
    input_data = {
        "blocked_task_id": "t1",
        "root_cause": "RC",
        "trace_id": "trace-123",
        "timestamp": "2026-05-02T12:00:00Z",
        "dependency_graph": graph
    }
    output = PropagationEngine.compute_dependency_output(input_data)
    
    expected_keys = {
        "blocked_task_id", "root_cause", "impacted_tasks", "impact_score",
        "severity", "resolution_signal", "trace_id", "timestamp"
    }
    assert set(output.keys()) == expected_keys
    assert output["impacted_tasks"] == ["t2"]
    assert output["impact_score"] == 1
    assert output["severity"] == "LOW"
    assert output["resolution_signal"] == "UNBLOCK_DEPENDENCY:RC"
    assert output["trace_id"] == "trace-123"

def test_severity_thresholds():
    # LOW: < 3
    graph_low = {"RC": ["t1"], "t1": ["t2", "t3"]}
    out_low = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "t1", "root_cause": "RC", 
        "trace_id": "TID", "timestamp": "TS", "dependency_graph": graph_low
    })
    assert out_low["impact_score"] == 2
    assert out_low["severity"] == "LOW"

    # MEDIUM: 3 <= impact_score < 10
    graph_med = {"RC": ["t1"], "t1": [f"t{i}" for i in range(2, 6)]} # length = 4
    out_med = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "t1", "root_cause": "RC", 
        "trace_id": "TID", "timestamp": "TS", "dependency_graph": graph_med
    })
    assert out_med["impact_score"] == 4
    assert out_med["severity"] == "MEDIUM"
    
    # HIGH: >= 10
    graph_high = {"RC": ["t1"], "t1": [f"t{i}" for i in range(2, 13)]} # length = 11
    out_high = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "t1", "root_cause": "RC", 
        "trace_id": "TID", "timestamp": "TS", "dependency_graph": graph_high
    })
    assert out_high["impact_score"] == 11
    assert out_high["severity"] == "HIGH"

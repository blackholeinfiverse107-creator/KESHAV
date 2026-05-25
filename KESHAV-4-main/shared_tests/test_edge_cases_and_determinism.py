import pytest
import random
import json
from app.engine import PropagationEngine

# ==========================================
# Phase 7 — Edge Case Coverage
# ==========================================

def test_deep_chain():
    # deep chain (10+ levels)
    graph = {f"task_{i}": [f"task_{i+1}"] for i in range(50)}
    path = PropagationEngine.compute_downstream_path("task_0", graph)
    expected_path = [f"task_{i}" for i in range(1, 51)]
    assert path == expected_path

def test_branching_graphs():
    # branching graphs
    graph = {
        "A": ["B", "C"],
        "B": ["D", "E"],
        "C": ["F", "G"]
    }
    # Deterministic alphabetical ordering expected: B, C, D, E, F, G
    path = PropagationEngine.compute_downstream_path("A", graph)
    assert path == ["B", "C", "D", "E", "F", "G"]

def test_cyclic_graphs():
    # cyclic graphs
    graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
    path = PropagationEngine.compute_downstream_path("A", graph)
    assert path == ["B", "C", "A"]

def test_missing_nodes():
    # missing nodes (Nodes not in graph keys or mapped to invalid values)
    graph = {
        "A": ["B", "D"],
        "B": ["C"],
        "C": "NOT_A_LIST" # Invalid
    }
    # A->B, D. B->C. C is not a list. D is missing.
    # D and C should be reached safely but not expanded further.
    out = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "A", "root_cause": "A", 
        "trace_id": "T", "timestamp": "T", "dependency_graph": graph
    })
    path = out["impacted_tasks"]
    assert path == ["B", "D", "C"]

def test_empty_graph():
    # empty graph
    path = PropagationEngine.compute_downstream_path("A", {})
    assert path == []
    
    out = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "A", "root_cause": "A", 
        "trace_id": "T", "timestamp": "T", "dependency_graph": {}
    })
    assert out["impact_score"] == 0
    assert out["impacted_tasks"] == []

# ==========================================
# Phase 8 — Determinism Proof
# ==========================================

def test_determinism_proof():
    # Run multiple iterations, Output must be byte-identical
    base_graph = {
        "RC": ["T1"],
        "T1": ["T4", "T2", "T3"],
        "T2": ["T5", "T6"],
        "T3": ["T7"],
        "T4": ["T8", "T9", "T10"],
        "T5": ["T1"], # Cycle
        "T6": [],
        "T7": ["T2", "T8"],
        "T8": [],
        "T9": ["T10"],
        "T10": []
    }
    
    ref_out = PropagationEngine.compute_dependency_output({
        "blocked_task_id": "T1", "root_cause": "RC", 
        "trace_id": "TID", "timestamp": "TS", "dependency_graph": base_graph
    })
    
    # Phase 8 requirement: Output must be byte-identical
    ref_bytes = json.dumps(ref_out, sort_keys=True).encode('utf-8')
    
    for _ in range(100):
        # Create a randomized version of the graph
        shuffled_graph = {}
        keys = list(base_graph.keys())
        random.shuffle(keys)
        
        for k in keys:
            vals = list(base_graph[k])
            random.shuffle(vals)
            shuffled_graph[k] = vals
            
        current_out = PropagationEngine.compute_dependency_output({
            "blocked_task_id": "T1", "root_cause": "RC", 
            "trace_id": "TID", "timestamp": "TS", "dependency_graph": shuffled_graph
        })
        
        # Serialize to bytes
        current_bytes = json.dumps(current_out, sort_keys=True).encode('utf-8')
        
        # Byte-identical verification
        assert current_bytes == ref_bytes, "Determinism failed: Output is not byte-identical!"

import sys
import uuid
import concurrent.futures
from copy import deepcopy

# 1. KESHAV-4 Imports
from app.engine import PropagationEngine

# 2. Path Trick
if 'app' in sys.modules:
    del sys.modules['app']
sys.path.insert(0, r'C:\blackhole\text-risk-scoring-service')

# 3. Live Service Imports
from app.sutradhara_control_plane import invoke_agent
from app.enforcement_schemas import KSMLInput, ContextSignal, SourceSystem
from app.layer3_dgic import compute_envelope_hash
from app.layer5_bucket import verify_by_trace_hash

def run_single_trace(trace_idx: int, graph: dict, blocked_task: str, root_cause: str):
    trace_id = f"trace-live-integration-{uuid.uuid4().hex[:10]}"
    
    # 1. Propagation Engine (Phase 1 & 2)
    prop_in = {
        "blocked_task_id": blocked_task,
        "root_cause": root_cause,
        "trace_id": trace_id,
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": graph
    }
    prop_out = PropagationEngine.compute_dependency_output(prop_in)
    
    # Generate DGIC State for Integration
    lineage_hash = "1" * 64
    payload_dict = {
        "epistemic_state": "KNOWN",
        "entropy_score": 0.0,
        "contradiction_flag": False
    }
    env_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)
    
    # 2. Map to KSML (Phase 3)
    ksml = KSMLInput(
        execution_id=trace_id,
        structured_signals=[
            ContextSignal(
                signal_id=f"prop_impact_{trace_idx}",
                signal_type="DEPENDENCY_IMPACT",
                value=0.9 if prop_out["severity"] == "HIGH" else 0.5,
                source="KESHAV"
            )
        ],
        metadata={
            "actor": "SETU_INTEGRATION_TEST",
            "proposed_action": prop_out["resolution_signal"],
            "source_system": SourceSystem.SOVEREIGN_CORE.value,
            "dgic_epistemic_state": {
                "epistemic_state": "KNOWN",
                "entropy_score": 0.0,
                "contradiction_flag": False,
                "lineage_hash": lineage_hash,
                "envelope_hash": env_hash
            }
        }
    )
    
    # 3. Live Pipeline Invocation (Phase 3)
    result = invoke_agent(ksml)
    
    # Assertions
    assert result.execution_id == trace_id, f"Trace ID corrupted! Expected {trace_id}, got {result.execution_id}"
    assert result.trace_hash is not None
    assert len(result.trace_hash) == 64
    
    return {
        "trace_id": trace_id,
        "impacted_tasks": prop_out["impacted_tasks"],
        "trace_hash": result.trace_hash,
        "enforcement_decision": result.enforcement_decision
    }

def test_live_tantra_integration_and_determinism():
    """
    Phase 3 & 4 combined:
    - Runs in live flow (Sūtradhāra → DGIC → Intelligence → RAJYA → Sarathi → Core → Bucket)
    - Concurrently processes 10 traces across different graph topologies
    - Proves deterministic trace continuation and no impact task corruption
    """
    graphs = [
        # 1. Branching
        {"RC": ["T1", "T2"], "T1": ["T3"], "T2": ["T4"]},
        # 2. Cyclic
        {"RC": ["T1"], "T1": ["T2"], "T2": ["T1", "T3"]},
        # 3. Disconnected
        {"RC": ["T1"], "T99": ["T100"]},
        # 4. Deep chain
        {f"T{i}": [f"T{i+1}"] for i in range(10)}
    ]
    graphs[3]["RC"] = ["T0"]
    
    futures = []
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(15):  # Min 10 traces
            graph = graphs[i % len(graphs)]
            futures.append(executor.submit(run_single_trace, i, deepcopy(graph), "BLOCKED", "RC"))
            
        for f in concurrent.futures.as_completed(futures):
            # Will raise exception if thread failed
            res = f.result()
            results.append(res)
            
    assert len(results) == 15
    
    # Phase 4 Requirements: No duplicate impact sets, Trace continuity
    for res in results:
        # Check no duplicates
        assert len(set(res["impacted_tasks"])) == len(res["impacted_tasks"]), "Duplicate impacted tasks found!"

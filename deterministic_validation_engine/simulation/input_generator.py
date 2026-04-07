import uuid
import random

def generate_pipeline_input(num_tasks=10, error_mode=None) -> dict:
    """
    Generates deterministic or intentionally broken mock inputs for testing.
    error_mode: 'disconnected', 'invalid_deps', 'all_valid', 'all_invalid', 'mixed'
    """
    # Fix seed for determinism in testing
    rng = random.Random(num_tasks)
    
    execution_id = f"exec_{uuid.uuid4()}"
    tasks = []
    c_res = []
    p_res = []
    
    for i in range(1, num_tasks + 1):
        task_id = f"task_{i}"
        tasks.append({"task_id": task_id, "type": "compute", "depends": []})
        
        valid = True
        if error_mode == 'all_invalid':
            valid = False
        elif error_mode == 'mixed' and i % 3 == 0:
            valid = False
            
        c_res.append({"task_id": task_id, "valid": valid, "metric": rng.random()})
        
        impact_score = rng.randint(10, 50) if valid else rng.randint(80, 100)
        impact_chain = [task_id]
        p_res.append({
            "task_id": task_id, 
            "impact_score": impact_score, 
            "impact_chain": impact_chain
        })
        
    bottleneck = {
        "root_cause": p_res[0]["task_id"],
        "impact_score": p_res[0]["impact_score"]
    }
    
    # Sort p_res to find max impact to assign to bottleneck
    max_p = max(p_res, key=lambda x: x["impact_score"])
    bottleneck["root_cause"] = max_p["task_id"]
    bottleneck["impact_score"] = max_p["impact_score"]

    payload = {
        "execution_id": execution_id,
        "tasks": tasks,
        "constraint_results": c_res,
        "propagation_results": p_res,
        "bottleneck_output": bottleneck
    }
    
    if error_mode == "invalid_deps":
        payload["bottleneck_output"]["root_cause"] = "unknown_task_404"
        
    if error_mode == "disconnected":
        # Violate constraint -> propagation linkage
        for c in payload["constraint_results"]:
            c["valid"] = False
        payload["propagation_results"] = []
        
    return payload

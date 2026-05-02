from typing import Dict, Any, List

def validate_schema(data: Dict[str, Any]) -> None:
    """Phase 1: Strict Contract Enforcement. Raises ValueError on schema deviation."""
    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary")
        
    required_keys = {"execution_id", "tasks", "constraint_results", "propagation_results", "bottleneck_output"}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        raise ValueError(f"Missing required keys: {missing_keys}")

    if not isinstance(data["tasks"], list):
        raise ValueError("tasks must be a list")

    for cr in data["constraint_results"]:
        if not {"task_id", "is_valid", "unsatisfied_dependencies"}.issubset(cr.keys()):
            raise ValueError(f"Invalid constraint_results schema: {cr}")

    for pr in data["propagation_results"]:
        if not {"task_id", "affected_tasks", "impact_score"}.issubset(pr.keys()):
            raise ValueError(f"Invalid propagation_results schema: {pr}")

    bo = data["bottleneck_output"]
    if not {"task_id", "root_cause", "impact_score"}.issubset(bo.keys()):
        raise ValueError(f"Invalid bottleneck_output schema: {bo}")

def check_constraint_propagation(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Phase 2: Constraint -> Propagation Validation."""
    violations = []
    prop_tasks = {pr["task_id"]: pr for pr in data["propagation_results"]}
    
    for cr in data["constraint_results"]:
        if not cr.get("is_valid", True):
            tid = cr["task_id"]
            if tid not in prop_tasks:
                violations.append({
                    "type": "CONSTRAINT_PROPAGATION_MISMATCH",
                    "task_id": tid,
                    "reason": "Invalid task does not appear in propagation_results."
                })
            else:
                affected = prop_tasks[tid].get("affected_tasks", [])
                if not affected:
                    violations.append({
                        "type": "CONSTRAINT_PROPAGATION_MISMATCH",
                        "task_id": tid,
                        "reason": "Invalid task does not affect downstream tasks."
                    })
    return violations

def check_propagation_bottleneck(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Phase 3: Propagation -> Bottleneck Validation."""
    violations = []
    bo = data["bottleneck_output"]
    b_task_id = bo["task_id"]
    prop_results = data["propagation_results"]
    
    prop_tasks = {pr["task_id"]: pr for pr in prop_results}
    
    if b_task_id not in prop_tasks:
        violations.append({
            "type": "BOTTLENECK_INVALID",
            "task_id": b_task_id,
            "reason": "Bottleneck task does not exist in propagation_results."
        })
        return violations
        
    max_impact = max((pr.get("impact_score", 0) for pr in prop_results), default=0)
    
    # Bottleneck task impact must be the max
    if prop_tasks[b_task_id].get("impact_score", 0) < max_impact:
         violations.append({
            "type": "BOTTLENECK_INVALID",
            "task_id": b_task_id,
            "reason": f"Bottleneck task does not have maximum impact_score (max is {max_impact})."
        })
         
    return violations

def check_root_cause(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Phase 4: Root Cause Validation."""
    violations = []
    bo = data["bottleneck_output"]
    root_cause = bo.get("root_cause")
    b_task_id = bo.get("task_id")
    
    task_ids = {t["task_id"] for t in data["tasks"] if "task_id" in t}
    
    if root_cause not in task_ids:
         violations.append({
            "type": "INVALID_ROOT_CAUSE",
            "task_id": root_cause or "UNKNOWN",
            "reason": "root_cause does not exist in task list."
        })
         return violations
         
    # Build graph from tasks to trace dependency chain of the bottleneck task
    # We trace backwards from the blocked task (b_task_id) to see if root_cause is an ancestor
    deps = {t["task_id"]: t.get("depends_on", []) for t in data["tasks"] if "task_id" in t}
    
    # Also include unsatisfied dependencies
    for cr in data["constraint_results"]:
        tid = cr["task_id"]
        unsatisfied = cr.get("unsatisfied_dependencies", [])
        if tid in deps:
            for u in unsatisfied:
                if u not in deps[tid]:
                    deps[tid].append(u)
                    
    def is_in_dependency_chain(start_task, target_task, visited=None):
        if visited is None:
            visited = set()
        if start_task == target_task:
            return True
        if start_task in visited:
            return False
        visited.add(start_task)
        for dep in deps.get(start_task, []):
            if is_in_dependency_chain(dep, target_task, visited):
                return True
        return False

    if not is_in_dependency_chain(b_task_id, root_cause):
         violations.append({
            "type": "INVALID_ROOT_CAUSE",
            "task_id": root_cause,
            "reason": f"root_cause {root_cause} does not appear in dependency chain of blocked task {b_task_id}."
        })
         
    return violations

def check_unsatisfied_dependencies(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Phase 5: Unsatisfied Dependency Validation."""
    violations = []
    
    task_map = {t["task_id"]: t for t in data["tasks"] if "task_id" in t}
    # Infer 'DONE' status: either status is 'DONE' or its constraint result is_valid=True
    # Let's map constraint results
    cr_valid = {cr["task_id"]: cr.get("is_valid", True) for cr in data["constraint_results"]}
    
    def is_done(tid):
        if tid not in task_map:
            return False
        t = task_map[tid]
        if t.get("status") == "DONE":
            return True
        # If explicitly marked as valid in constraints
        if cr_valid.get(tid) is True:
            return True
        return False
        
    for cr in data["constraint_results"]:
        tid = cr["task_id"]
        for u_dep in cr.get("unsatisfied_dependencies", []):
            if u_dep not in task_map:
                 violations.append({
                    "type": "DEPENDENCY_MISMATCH",
                    "task_id": tid,
                    "reason": f"Unsatisfied dependency {u_dep} does not exist in task list."
                })
            elif is_done(u_dep):
                 violations.append({
                    "type": "DEPENDENCY_MISMATCH",
                    "task_id": tid,
                    "reason": f"Unsatisfied dependency {u_dep} is unexpectedly marked as DONE."
                })
                
    return violations

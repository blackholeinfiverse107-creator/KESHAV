from typing import Dict, List, Set
from shared_schemas.schemas import PropagationOutput, PropagationInput, PropagationContractViolation

class PropagationEngine:


    @staticmethod
    def compute_downstream_path(blocked_task_id: str, dependency_graph: Dict[str, List[str]]) -> List[str]:
        """
        Phase 2: Computes the full downstream path using a deterministic Breadth-First Search.
        Strict ordering is enforced by sorting neighbors.
        No duplicates are allowed.
        """
        impacted_tasks: List[str] = []
        visited: Set[str] = set()
        queue: List[str] = []
        
        if blocked_task_id in dependency_graph:
            initial_deps = sorted(dependency_graph[blocked_task_id])
            for dep in initial_deps:
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
                    impacted_tasks.append(dep)
                    
        while queue:
            current_task = queue.pop(0)
            if current_task in dependency_graph:
                # Enforce determinism by sorting neighbors
                neighbors = sorted(dependency_graph[current_task])
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
                        impacted_tasks.append(neighbor)
                        
        return impacted_tasks

    @staticmethod
    def compute_dependency_output(input_data: dict) -> dict:
        """
        Generates the decision-grade dependency intelligence output.
        Fails closed on schema mismatch, invalid graph, malformed trace_id, or broken root cause chain.
        """
        try:
            valid_input = PropagationInput.model_validate(input_data)
        except Exception as e:
            raise PropagationContractViolation("SCHEMA_MISMATCH", f"Input validation failed: {str(e)}")

        blocked_task_id = valid_input.blocked_task_id
        root_cause = valid_input.root_cause
        trace_id = valid_input.trace_id
        timestamp = valid_input.timestamp
        dependency_graph = valid_input.dependency_graph
        
        # Verify root cause exists in the graph
        if root_cause not in dependency_graph:
            raise PropagationContractViolation("BROKEN_ROOT_CAUSE", f"Root cause {root_cause} not found in dependency graph")
        
        # Verify blocked_task_id exists in the graph
        if blocked_task_id not in dependency_graph:
            raise PropagationContractViolation("INVALID_GRAPH", f"Blocked task {blocked_task_id} not found in dependency graph")
        
        # Phase 2: Propagation Truth Verifier
        impacted_tasks = PropagationEngine.compute_downstream_path(blocked_task_id, dependency_graph)
        
        # Phase 3: Zero-State Handling
        impact_score = len(impacted_tasks)
        
        # Severity thresholds
        if impact_score < 3:
            severity = "LOW"
        elif impact_score < 10:
            severity = "MEDIUM"
        else:
            severity = "HIGH"
            
        resolution_signal = f"UNBLOCK_DEPENDENCY:{root_cause}"
            
        output = PropagationOutput(
            blocked_task_id=blocked_task_id,
            root_cause=root_cause,
            impacted_tasks=impacted_tasks,
            impact_score=impact_score,
            severity=severity,
            resolution_signal=resolution_signal,
            trace_id=trace_id,
            timestamp=timestamp
        )
        
        return output.model_dump()
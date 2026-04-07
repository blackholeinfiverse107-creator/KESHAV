"""
invariants.py — Phase 3: Cross-Layer Consistency Validation
===========================================================
Enforces invariant safety across logical boundaries.
"""

from .snapshot import PipelineSnapshot

def validate_cross_layer_consistency(snapshot: PipelineSnapshot) -> dict:
    """
    Verifies 3 primary invariants:
    1. Constraint -> Propagation: Invalid tasks must appear in propagation impact chains.
    2. Propagation -> Bottleneck: Bottleneck must have highest impact_score.
    3. Root cause validity: Root cause must exist in the task graph.
    """
    tasks = snapshot.tasks
    c_res = snapshot.constraint_results
    p_res = snapshot.propagation_results
    b_out = snapshot.bottleneck_output

    # 1. Constraint -> Propagation
    invalid_tasks = {c['task_id'] for c in c_res if not c.get('valid', True)}
    propagation_chain_tasks = set()
    for p in p_res:
        propagation_chain_tasks.update(p.get('impact_chain', []))
    
    constraint_propagation = True
    if invalid_tasks and not invalid_tasks.issubset(propagation_chain_tasks):
        constraint_propagation = False

    # 2. Propagation -> Bottleneck
    propagation_bottleneck = True
    if p_res and b_out:
        max_impact = max((p.get('impact_score', 0) for p in p_res), default=0)
        if b_out.get('impact_score', 0) < max_impact and max_impact > 0:
            propagation_bottleneck = False

    # 3. Root cause validity
    task_ids = {t['task_id'] for t in tasks}
    root_cause_valid = True
    root_cause = b_out.get('root_cause')
    if root_cause and root_cause not in task_ids:
        root_cause_valid = False

    return {
        "constraint_propagation": constraint_propagation,
        "propagation_bottleneck": propagation_bottleneck,
        "root_cause_valid": root_cause_valid
    }

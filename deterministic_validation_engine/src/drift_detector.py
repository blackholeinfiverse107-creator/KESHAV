"""
drift_detector.py — Phase 5: Drift Detection
=============================================
Detects mismatches across runs, inconsistent ordering, and missing linkages.
"""

import copy

def detect_drift(run1_snapshot, run2_snapshot) -> list:
    """
    Compare two snapshots for deterministic identicality.
    Returns list of violation strings.
    """
    violations = []
    
    # 1. Content Identity (Order & Value mismatch)
    if not run1_snapshot.matches(run2_snapshot):
        violations.append("DRIFT_DETECTED: Snapshots generated different content hashes across runs.")
    
    # 2. Strict Ordering verification
    list1_tasks = [t['task_id'] for t in run1_snapshot.tasks]
    list2_tasks = [t['task_id'] for t in run2_snapshot.tasks]
    if list1_tasks != list2_tasks:
        violations.append("ORDERING_VIOLATION: Tasks order changed across runs.")
        
    list1_cres = [c['task_id'] for c in run1_snapshot.constraint_results]
    list2_cres = [c['task_id'] for c in run2_snapshot.constraint_results]
    if list1_cres != list2_cres:
        violations.append("ORDERING_VIOLATION: Constraint results order changed across runs.")
        
    list1_pres = [p['task_id'] for p in run1_snapshot.propagation_results]
    list2_pres = [p['task_id'] for p in run2_snapshot.propagation_results]
    if list1_pres != list2_pres:
        violations.append("ORDERING_VIOLATION: Propagation results order changed across runs.")

    # 3. Missing Linkage Verification
    task_ids = {t['task_id'] for t in run1_snapshot.tasks}
    unlinked_cres = [c['task_id'] for c in run1_snapshot.constraint_results if c['task_id'] not in task_ids]
    unlinked_pres = [p['task_id'] for p in run1_snapshot.propagation_results if p['task_id'] not in task_ids]
    
    if unlinked_cres:
        violations.append(f"MISSING_LINKAGE: Constraint results reference unknown tasks {unlinked_cres}")
    if unlinked_pres:
        violations.append(f"MISSING_LINKAGE: Propagation results reference unknown tasks {unlinked_pres}")

    return violations

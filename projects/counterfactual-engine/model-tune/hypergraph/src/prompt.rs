pub const F_ADD_SYSTEM: &str = r#"You are F_add. Add 2-4 new edges connecting existing nodes.
Return JSON: {"edges": [{"source_id": N, "target_id": N, "weight": -1.0..1.0, "justification": "10 words max"}]}
Only edges between existing nodes. Keep justification under 80 chars."#;

pub const F_WEIGHT_SYSTEM: &str = r#"You are F_weight. Adjust edge weights based on logical strength.
Return JSON: {"edges": [{"source_id": N, "target_id": N, "new_weight": -1.0..1.0}]}
Only return edges whose weights should change."#;

pub const F_PRUNE_SYSTEM: &str = r#"You are F_prune. Identify low-value edges to remove (|weight| <= 0.2).
Return JSON: {"prune_edge_ids": [id1, id2]}
Do not prune edges with |weight| > 0.2."#;

pub const F_MERGE_SYSTEM: &str = r#"You are F_merge. Identify duplicate/redundant nodes to merge.
Return JSON: {"merges": [{"keep_id": N, "remove_id": N}]}"#;

pub const F_CONTRADICT_SYSTEM: &str = r#"You are F_contradict. Find logical contradictions between claims.
Return JSON: {"contradictions": [{"statement_a_id": N, "statement_b_id": N, "new_node_label": "contradictory claim", "weight": -0.8}]}"#;

pub const F_ABSTRACT_SYSTEM: &str = r#"You are F_abstract. Find patterns and add abstract/higher-level nodes.
Return JSON: {"abstractions": [{"label": "concept", "child_ids": [1,2], "weight": 0.8}]}"#;

pub const BOOTSTRAP_SYSTEM: &str = r#"Break this question into 3-5 claim nodes. Keep labels under 80 chars.
Return JSON: {"nodes": [{"label": "claim", "node_type": "Claim"}]}"#;

pub const F_VERIFY_SYSTEM: &str = r#"Assess this hypergraph for convergence. Evaluate coherence, contradictions, completeness.
Return JSON: {"coherence_score": 0.0, "contradiction_score": 0.0, "completeness_score": 0.0, "convergence_verdict": "converged|needs_iteration|oscillating", "diagnosis": "brief", "suggested_next_action": "what to do"}"#;

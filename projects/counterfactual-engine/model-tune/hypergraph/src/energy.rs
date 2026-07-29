use crate::hypergraph::Graph;

pub fn compute(graph: &Graph) -> f64 {
    let mut total_weight = 0.0_f64;
    let mut agreement = 0.0_f64;
    let mut conflict = 0.0_f64;

    for edge in &graph.edges {
        total_weight += edge.weight.abs();
        if edge.weight > 0.0 {
            agreement += edge.weight;
        } else {
            conflict += edge.weight.abs();
        }
    }

    if total_weight == 0.0 {
        return 0.0;
    }

    (agreement - conflict) / total_weight
}

pub fn check_convergence(
    graph: &Graph,
    min_rounds: u32,
    max_rounds: u32,
    epsilon: f64,
) -> bool {
    if graph.meta.round < min_rounds {
        return false;
    }
    if graph.meta.round >= max_rounds {
        return true;
    }
    let hist = &graph.meta.energy_history;
    if hist.len() < 3 {
        return false;
    }
    let last = hist[hist.len() - 1];
    let prev = hist[hist.len() - 2];
    (last - prev).abs() < epsilon
}

pub fn extract_answer(graph: &Graph) -> Option<String> {
    if graph.nodes.len() < 2 {
        return None;
    }
    let mut best_path: Vec<(f64, String)> = vec![];
    let root_id = 0;

    let answer_nodes: Vec<&crate::hypergraph::Node> = graph
        .nodes
        .iter()
        .filter(|n| matches!(n.node_type, crate::hypergraph::NodeType::Answer))
        .collect();

    for answer in &answer_nodes {
        let mut visited = std::collections::HashSet::new();
        if let Some(path) = find_best_path(graph, root_id, answer.id, &mut visited, 0) {
            best_path.push(path);
        }
    }

    if best_path.is_empty() {
        let all_paths: Vec<_> = graph
            .nodes
            .iter()
            .filter(|n| n.id != root_id)
            .filter_map(|n| {
                let mut visited = std::collections::HashSet::new();
                find_best_path(graph, root_id, n.id, &mut visited, 0)
            })
            .collect();
        if all_paths.is_empty() {
            return None;
        }
        let best = all_paths.into_iter().max_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        return best.map(|(_, s)| s);
    }

    best_path.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());
    Some(best_path[0].1.clone())
}

fn find_best_path(
    graph: &Graph,
    current: u64,
    target: u64,
    visited: &mut std::collections::HashSet<u64>,
    depth: usize,
) -> Option<(f64, String)> {
    if current == target {
        let node = graph.get_node(current)?;
        return Some((0.0, node.label.clone()));
    }
    if depth > 50 || !visited.insert(current) {
        return None;
    }
    let edges = graph.edges_from(current);
    let mut candidates: Vec<(f64, String)> = vec![];
    for edge in &edges {
        if let Some(sub) = find_best_path(graph, edge.target, target, visited, depth + 1) {
            let path_score = edge.weight + sub.0;
            let node = graph.get_node(current)?;
            let just = edge
                .justification
                .as_deref()
                .unwrap_or("(no justification)");
            let label = format!("{} -> {} [{}]\n  ∵ {}", node.label, sub.1, edge.model, just);
            candidates.push((path_score, label));
        }
    }
    visited.remove(&current);
    candidates.into_iter().max_by(|a, b| a.0.partial_cmp(&b.0).unwrap())
}

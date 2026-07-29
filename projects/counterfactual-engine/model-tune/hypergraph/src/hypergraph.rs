use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: u64,
    pub label: String,
    pub node_type: NodeType,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeType {
    Question,
    Claim,
    Fact,
    Contradiction,
    Answer,
    Abstract,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub id: u64,
    pub source: u64,
    pub target: u64,
    pub weight: f64,
    pub operator: OperatorId,
    pub model: String,
    pub round: u32,
    pub justification: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum OperatorId {
    Add,
    Weight,
    Prune,
    Merge,
    Contradict,
    Abstract,
    Verify,
}

impl std::fmt::Display for OperatorId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OperatorId::Add => write!(f, "F_add"),
            OperatorId::Weight => write!(f, "F_weight"),
            OperatorId::Prune => write!(f, "F_prune"),
            OperatorId::Merge => write!(f, "F_merge"),
            OperatorId::Contradict => write!(f, "F_contradict"),
            OperatorId::Abstract => write!(f, "F_abstract"),
            OperatorId::Verify => write!(f, "F_verify"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphMeta {
    pub question: String,
    pub question_id: String,
    pub round: u32,
    pub energy_history: Vec<f64>,
    pub converged: bool,
    pub created_at: String,
    pub completed_at: Option<String>,
    pub total_rounds: u32,
    pub answer: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Graph {
    pub nodes: Vec<Node>,
    pub edges: Vec<Edge>,
    pub meta: GraphMeta,
    next_node_id: u64,
    next_edge_id: u64,
}

impl Graph {
    pub fn new(question: &str) -> Self {
        let id = uuid::Uuid::new_v4().to_string();
        let root = Node {
            id: 0,
            label: question.to_string(),
            node_type: NodeType::Question,
            metadata: HashMap::new(),
        };
        let now = chrono::Utc::now().to_rfc3339();
        Graph {
            nodes: vec![root],
            edges: vec![],
            meta: GraphMeta {
                question: question.to_string(),
                question_id: id,
                round: 0,
                energy_history: vec![],
                converged: false,
                created_at: now,
                completed_at: None,
                total_rounds: 0,
                answer: None,
            },
            next_node_id: 1,
            next_edge_id: 1,
        }
    }

    pub fn add_node(&mut self, label: &str, node_type: NodeType) -> u64 {
        let id = self.next_node_id;
        self.next_node_id += 1;
        self.nodes.push(Node {
            id,
            label: label.to_string(),
            node_type,
            metadata: HashMap::new(),
        });
        id
    }

    pub fn add_edge(
        &mut self,
        source: u64,
        target: u64,
        weight: f64,
        operator: OperatorId,
        model: &str,
        round: u32,
        justification: Option<String>,
    ) -> u64 {
        let id = self.next_edge_id;
        self.next_edge_id += 1;
        self.edges.push(Edge {
            id,
            source,
            target,
            weight,
            operator,
            model: model.to_string(),
            round,
            justification,
        });
        id
    }

    pub fn get_node(&self, id: u64) -> Option<&Node> {
        self.nodes.iter().find(|n| n.id == id)
    }

    pub fn edges_from(&self, node_id: u64) -> Vec<&Edge> {
        self.edges.iter().filter(|e| e.source == node_id).collect()
    }

    pub fn edges_to(&self, node_id: u64) -> Vec<&Edge> {
        self.edges.iter().filter(|e| e.target == node_id).collect()
    }

    pub fn remove_edge(&mut self, id: u64) {
        self.edges.retain(|e| e.id != id);
    }

    pub fn remove_node(&mut self, id: u64) {
        self.nodes.retain(|n| n.id != id);
        self.edges.retain(|e| e.source != id && e.target != id);
    }

    pub fn prune_edges_below(&mut self, threshold: f64) -> usize {
        let before = self.edges.len();
        self.edges.retain(|e| e.weight >= threshold);
        before - self.edges.len()
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    pub fn memory_estimate_bytes(&self) -> usize {
        self.nodes.len() * 256 + self.edges.len() * 128
    }

    pub fn suggest_prune(&self) -> f64 {
        let weights: Vec<f64> = self.edges.iter().map(|e| e.weight).collect();
        if weights.is_empty() {
            return 0.0;
        }
        let mut sorted = weights.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let mid = sorted.len() / 2;
        sorted[mid]
    }
}

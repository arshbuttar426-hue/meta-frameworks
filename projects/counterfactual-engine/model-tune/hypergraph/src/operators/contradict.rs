use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, NodeType, OperatorId};
use crate::prompt::F_CONTRADICT_SYSTEM;

const MODEL: &str = "nvidia/nemotron-3-nano-30b-a3b:free";

pub struct ContradictOperator {
    client: Box<dyn Client>,
}

impl ContradictOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        ContradictOperator { client }
    }
}

#[derive(Deserialize)]
struct ContradictResponse {
    contradictions: Vec<Contradiction>,
}

#[derive(Deserialize)]
struct Contradiction {
    statement_a_id: u64,
    statement_b_id: u64,
    new_node_label: String,
    weight: f64,
}

#[async_trait]
impl Operator for ContradictOperator {
    fn id(&self) -> OperatorId { OperatorId::Contradict }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_contradict ({})...", MODEL);
        let nodes: Vec<String> = graph.nodes.iter().map(|n| format!("  id={}: {} ({:?})", n.id, n.label, n.node_type)).collect();
        let user = format!("Nodes:\n{}\n\nReturn contradictions as JSON.", nodes.join("\n"));
        let (raw, _) = self.client.call(MODEL, F_CONTRADICT_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: ContradictResponse = serde_json::from_str(&json).map_err(|e| anyhow::anyhow!("JSON: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        for c in &parsed.contradictions {
            let nid = g.add_node(&c.new_node_label, NodeType::Contradiction);
            g.add_edge(c.statement_a_id, nid, c.weight.clamp(-1.0, -0.5), OperatorId::Contradict, MODEL, graph.meta.round + 1, Some(format!("contra id={}", c.statement_b_id)));
            g.add_edge(c.statement_b_id, nid, c.weight.clamp(-1.0, -0.5), OperatorId::Contradict, MODEL, graph.meta.round + 1, Some(format!("contra id={}", c.statement_a_id)));
        }
        Ok((g, OperatorResult { operator: OperatorId::Contradict, model: MODEL.to_string(), round: graph.meta.round + 1, summary: format!("F_contradict: {} contra", parsed.contradictions.len()) }))
    }
}

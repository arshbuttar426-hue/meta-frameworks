use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, NodeType, OperatorId};
use crate::prompt::F_ABSTRACT_SYSTEM;

const MODEL: &str = "poolside/laguna-xs.2:free";

pub struct AbstractOperator {
    client: Box<dyn Client>,
}

impl AbstractOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        AbstractOperator { client }
    }
}

#[derive(Deserialize)]
struct AbstractResponse {
    abstractions: Vec<Abstraction>,
}

#[derive(Deserialize)]
struct Abstraction {
    label: String,
    child_ids: Vec<u64>,
    weight: f64,
}

#[async_trait]
impl Operator for AbstractOperator {
    fn id(&self) -> OperatorId { OperatorId::Abstract }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_abstract ({})...", MODEL);
        let nodes: Vec<String> = graph.nodes.iter().map(|n| format!("  id={}: {} ({:?})", n.id, n.label, n.node_type)).collect();
        let user = format!("Nodes:\n{}\n\nReturn abstractions as JSON.", nodes.join("\n"));
        let (raw, _) = self.client.call(MODEL, F_ABSTRACT_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: AbstractResponse = serde_json::from_str(&json).map_err(|e| anyhow::anyhow!("JSON: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        for a in &parsed.abstractions {
            let aid = g.add_node(&a.label, NodeType::Abstract);
            for child in &a.child_ids {
                if g.get_node(*child).is_some() {
                    g.add_edge(aid, *child, a.weight.clamp(0.0, 1.0), OperatorId::Abstract, MODEL, graph.meta.round + 1, None);
                }
            }
        }
        Ok((g, OperatorResult { operator: OperatorId::Abstract, model: MODEL.to_string(), round: graph.meta.round + 1, summary: format!("F_abstract: {} abstractions", parsed.abstractions.len()) }))
    }
}

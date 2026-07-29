use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, OperatorId};
use crate::prompt::F_WEIGHT_SYSTEM;

const MODEL: &str = "poolside/laguna-xs.2:free";

pub struct WeightOperator {
    client: Box<dyn Client>,
}

impl WeightOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        WeightOperator { client }
    }
}

#[derive(Deserialize)]
struct WeightResponse {
    edges: Vec<WeightEdge>,
}

#[derive(Deserialize)]
struct WeightEdge {
    source_id: u64,
    target_id: u64,
    new_weight: f64,
}

#[async_trait]
impl Operator for WeightOperator {
    fn id(&self) -> OperatorId { OperatorId::Weight }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_weight ({})...", MODEL);
        let edges: Vec<String> = graph.edges.iter().map(|e| format!("  #{}: n{}->n{} w={}", e.id, e.source, e.target, e.weight)).collect();
        let user = format!("Edges:\n{}\n\nReturn reweighted edges as JSON.", edges.join("\n"));
        let (raw, _) = self.client.call(MODEL, F_WEIGHT_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: WeightResponse = serde_json::from_str(&json).map_err(|e| anyhow::anyhow!("JSON: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        let mut changed = 0usize;
        for we in &parsed.edges {
            for edge in g.edges.iter_mut() {
                if edge.source == we.source_id && edge.target == we.target_id {
                    edge.weight = we.new_weight.clamp(-1.0, 1.0); changed += 1;
                }
            }
        }
        Ok((g, OperatorResult { operator: OperatorId::Weight, model: MODEL.to_string(), round: graph.meta.round + 1, summary: format!("F_weight: reweighted {} edges", changed) }))
    }
}

use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, OperatorId};
use crate::prompt::F_PRUNE_SYSTEM;

const MODEL: &str = "poolside/laguna-xs.2:free";

pub struct PruneOperator {
    client: Box<dyn Client>,
}

impl PruneOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        PruneOperator { client }
    }
}

#[derive(Deserialize)]
struct PruneResponse {
    prune_edge_ids: Vec<u64>,
}

#[async_trait]
impl Operator for PruneOperator {
    fn id(&self) -> OperatorId { OperatorId::Prune }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_prune ({})...", MODEL);
        let edges: Vec<String> = graph.edges.iter().map(|e| format!("  #{}: n{}->n{} w={:.2}", e.id, e.source, e.target, e.weight)).collect();
        let user = format!("Edges:\n{}\n\nReturn edge IDs to prune as JSON.", edges.join("\n"));
        let (raw, _) = self.client.call(MODEL, F_PRUNE_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: PruneResponse = serde_json::from_str(&json).map_err(|e| anyhow::anyhow!("JSON: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        let mut pruned = 0usize;
        for id in &parsed.prune_edge_ids {
            if let Some(edge) = g.edges.iter().find(|e| e.id == *id) {
                if edge.weight.abs() <= 0.2 { g.remove_edge(*id); pruned += 1; }
            }
        }
        Ok((g, OperatorResult { operator: OperatorId::Prune, model: MODEL.to_string(), round: graph.meta.round + 1, summary: format!("F_prune: pruned {} edges", pruned) }))
    }
}

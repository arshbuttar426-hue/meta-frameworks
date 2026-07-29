use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, OperatorId};
use crate::prompt::F_ADD_SYSTEM;

const MODEL: &str = "hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M";

pub struct AddOperator {
    client: Box<dyn Client>,
    model: String,
}

impl AddOperator {
    pub fn new(client: Box<dyn Client>, model: &str) -> Self {
        AddOperator { client, model: model.to_string() }
    }
}

impl Default for AddOperator {
    fn default() -> Self {
        AddOperator::new(Box::new(crate::ollama::OllamaClient::new()), MODEL)
    }
}

#[derive(Deserialize)]
struct AddResponse {
    edges: Vec<AddEdge>,
}

#[derive(Deserialize)]
struct AddEdge {
    source_id: u64,
    target_id: u64,
    weight: f64,
    justification: String,
}

#[async_trait]
impl Operator for AddOperator {
    fn id(&self) -> OperatorId { OperatorId::Add }
    fn model_name(&self) -> &str { &self.model }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_add ({})...", &self.model);
        let nodes = graph.nodes.iter()
            .map(|n| format!("  id={}: {}", n.id, n.label)).collect::<Vec<_>>().join("\n");
        let user = format!("Nodes:\n{}\n\nReturn JSON with 2-3 new edges.", nodes);
        let (raw, _) = self.client.call(&self.model, F_ADD_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: AddResponse = serde_json::from_str(&json)
            .map_err(|e| anyhow::anyhow!("JSON parse: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        for edge in &parsed.edges {
            if g.get_node(edge.source_id).is_some() && g.get_node(edge.target_id).is_some() {
                g.add_edge(edge.source_id, edge.target_id, edge.weight.clamp(-1.0, 1.0), OperatorId::Add, &self.model, graph.meta.round + 1, Some(edge.justification.clone()));
            }
        }
        let summary = format!("F_add: added {} edges", parsed.edges.len());
        Ok((g, OperatorResult { operator: OperatorId::Add, model: self.model.clone(), round: graph.meta.round + 1, summary }))
    }
}

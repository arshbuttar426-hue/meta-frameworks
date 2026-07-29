use anyhow::Result;
use async_trait::async_trait;
use serde::Deserialize;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, OperatorId};
use crate::prompt::F_MERGE_SYSTEM;

const MODEL: &str = "openai/gpt-oss-20b:free";

pub struct MergeOperator {
    client: Box<dyn Client>,
}

impl MergeOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        MergeOperator { client }
    }
}

#[derive(Deserialize)]
struct MergeResponse {
    merges: Vec<MergePair>,
}

#[derive(Deserialize)]
struct MergePair {
    keep_id: u64,
    remove_id: u64,
}

#[async_trait]
impl Operator for MergeOperator {
    fn id(&self) -> OperatorId { OperatorId::Merge }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_merge ({})...", MODEL);
        let nodes: Vec<String> = graph.nodes.iter().map(|n| format!("  id={}: {} ({:?})", n.id, n.label, n.node_type)).collect();
        let user = format!("Nodes:\n{}\n\nReturn merge pairs as JSON.", nodes.join("\n"));
        let (raw, _) = self.client.call(MODEL, F_MERGE_SYSTEM, &user).await?;
        let json = crate::json_util::extract_json(&raw);
        let parsed: MergeResponse = serde_json::from_str(&json).map_err(|e| anyhow::anyhow!("JSON: {}\nRaw: {}", e, raw))?;
        let mut g = graph.clone();
        for m in &parsed.merges {
            if g.get_node(m.keep_id).is_none() || g.get_node(m.remove_id).is_none() { continue; }
            let eids: Vec<u64> = g.edges.iter().filter(|e| e.source == m.remove_id || e.target == m.remove_id).map(|e| e.id).collect();
            for eid in eids {
                if let Some(e) = g.edges.iter_mut().find(|e| e.id == eid) {
                    if e.source == m.remove_id { e.source = m.keep_id; }
                    if e.target == m.remove_id { e.target = m.keep_id; }
                }
            }
            g.remove_node(m.remove_id);
        }
        Ok((g, OperatorResult { operator: OperatorId::Merge, model: MODEL.to_string(), round: graph.meta.round + 1, summary: format!("F_merge: merged {} node pairs", parsed.merges.len()) }))
    }
}

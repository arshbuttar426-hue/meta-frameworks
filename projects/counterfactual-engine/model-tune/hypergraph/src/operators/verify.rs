use anyhow::{anyhow, Result};
use async_trait::async_trait;
use serde::Deserialize;
use serde_json::Value;

use super::{Client, Operator, OperatorResult};
use crate::hypergraph::{Graph, OperatorId};
use crate::prompt::F_VERIFY_SYSTEM;

const MODEL: &str = "openai/gpt-oss-20b:free";

pub struct VerifyOperator {
    client: Box<dyn Client>,
}

impl VerifyOperator {
    pub fn new(client: Box<dyn Client>) -> Self {
        VerifyOperator { client }
    }
}

#[derive(Deserialize)]
struct VerifyResponse {
    #[serde(default)]
    verdict: String,
    #[serde(default, alias = "convergence_verdict")]
    convergence_verdict: String,
    #[serde(default)]
    notes: String,
    #[serde(default)]
    diagnosis: String,
}

impl VerifyOperator {
    async fn call_api(&self, model: &str, system: &str, user: &str) -> Result<String> {
        let (content, _) = self.client.call(model, system, user).await?;
        let json_str = strip_fences(&content);
        let v: Value = serde_json::from_str(&json_str)
            .map_err(|e| anyhow!("Verify JSON parse: {}\nRaw: {}", e, content))?;
        let verdict = v.get("verdict")
            .or(v.get("convergence_verdict"))
            .and_then(|x| x.as_str())
            .unwrap_or("incomplete");
        Ok(verdict.to_string())
    }
}

fn strip_fences(s: &str) -> String {
    let s = s.trim();
    if s.starts_with("```json") {
        s.strip_prefix("```json").unwrap_or(s).strip_suffix("```").unwrap_or(s).trim().to_string()
    } else if s.starts_with("```") {
        s.strip_prefix("```").unwrap_or(s).strip_suffix("```").unwrap_or(s).trim().to_string()
    } else {
        let start = s.find('{').unwrap_or(0);
        let end = s.rfind('}').map(|i| i + 1).unwrap_or(s.len());
        s[start..end].to_string()
    }
}

#[async_trait]
impl Operator for VerifyOperator {
    fn id(&self) -> OperatorId { OperatorId::Verify }
    fn model_name(&self) -> &str { MODEL }

    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)> {
        eprintln!("    → F_verify ({})...", MODEL);
        let nodes: Vec<String> = graph.nodes.iter().map(|n| format!("  id={}: {} ({:?})", n.id, n.label, n.node_type)).collect();
        let edges: Vec<String> = graph.edges.iter().map(|e| format!("  #{}: n{}->n{} w={:.2}", e.id, e.source, e.target, e.weight)).collect();
        let user = format!(
            "Graph state:\nNodes:\n{}\n\nEdges:\n{}\n\nQuestion: {}\n\nReturn JSON with 'verdict' field (consistent/inconsistent/incomplete/converged/needs_iteration).",
            nodes.join("\n"), edges.join("\n"), graph.meta.question
        );
        let verdict = self.call_api(MODEL, F_VERIFY_SYSTEM, &user).await?;
        Ok((graph.clone(), OperatorResult {
            operator: OperatorId::Verify,
            model: MODEL.to_string(),
            round: graph.meta.round + 1,
            summary: format!("F_verify: {}", verdict),
        }))
    }
}

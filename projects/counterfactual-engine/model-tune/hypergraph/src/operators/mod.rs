pub mod add;
pub mod weight;
pub mod prune;
pub mod merge;
pub mod contradict;
pub mod abstract_;
pub mod verify;

use anyhow::Result;
use async_trait::async_trait;

use crate::api::Usage;
use crate::hypergraph::{Graph, OperatorId};

#[derive(Debug, Clone)]
pub struct OperatorResult {
    pub operator: OperatorId,
    pub model: String,
    pub round: u32,
    pub summary: String,
}

#[async_trait]
pub trait Client: Send + Sync {
    async fn call(&self, model: &str, system: &str, user: &str) -> Result<(String, Usage)>;
}

#[async_trait]
pub trait Operator: Send + Sync {
    fn id(&self) -> OperatorId;
    fn model_name(&self) -> &str;
    async fn execute(&self, graph: &Graph) -> Result<(Graph, OperatorResult)>;
}

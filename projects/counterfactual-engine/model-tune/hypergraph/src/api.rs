use anyhow::{anyhow, Result};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::time::Duration;

use crate::operators::Client;

#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<Message>,
    max_tokens: u32,
    temperature: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    role: String,
    #[serde(default)]
    content: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    reasoning: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ChatResponse {
    choices: Vec<Choice>,
    usage: Option<Usage>,
}

#[derive(Debug, Deserialize)]
struct Choice {
    message: Message,
}

#[derive(Debug, Deserialize)]
pub struct Usage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
}

pub struct ApiClient {
    api_key: String,
    base_url: String,
    client: reqwest::Client,
}

#[async_trait]
impl Client for ApiClient {
    async fn call(&self, model: &str, system: &str, user: &str) -> Result<(String, Usage)> {
        self._call(model, system, user).await
    }
}

impl ApiClient {
    pub fn new(api_key: &str) -> Self {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(45))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        ApiClient {
            api_key: api_key.to_string(),
            base_url: "https://openrouter.ai/api/v1".to_string(),
            client,
        }
    }

    pub async fn _call(&self, model: &str, system: &str, user: &str) -> Result<(String, Usage)> {
        let payload = ChatRequest {
            model: model.to_string(),
            messages: vec![
                Message { role: "system".to_string(), content: Some(system.to_string()), reasoning: None },
                Message { role: "user".to_string(), content: Some(user.to_string()), reasoning: None },
            ],
            max_tokens: 4096,
            temperature: 0.09,
        };

        let resp = self
            .client
            .post(format!("{}/chat/completions", self.base_url))
            .header("Authorization", format!("Bearer {}", self.api_key))
            .header("HTTP-Referer", "https://github.com/arshbuttar/hypergraph")
            .header("X-Title", "Hypergraph Engine")
            .json(&payload)
            .send()
            .await
            .map_err(|e| anyhow!("API call failed (model={}): {}", model, e))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(anyhow!("API error (model={}): {}", model, text));
        }

        let data: ChatResponse = resp
            .json()
            .await
            .map_err(|e| anyhow!("API JSON parse failed (model={}): {}", model, e))?;

        let msg = data
            .choices
            .into_iter()
            .next()
            .ok_or_else(|| anyhow!("API returned no choices (model={})", model))?
            .message;

        let content = msg.content
            .filter(|c| !c.trim().is_empty())
            .or(msg.reasoning.filter(|r| !r.trim().is_empty()))
            .unwrap_or_default();

        let usage = data.usage.unwrap_or(Usage { prompt_tokens: 0, completion_tokens: 0 });

        Ok((content, usage))
    }
}

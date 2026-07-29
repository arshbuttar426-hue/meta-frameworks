use anyhow::{anyhow, Result};
use async_trait::async_trait;
use serde::{Deserialize, Serialize, de::DeserializeOwned};
use std::time::Duration;

use crate::api::Usage;
use crate::operators::Client;

pub async fn call_json<T: DeserializeOwned>(
    model: &str,
    system: &str,
    user: &str,
    temperature: f64,
) -> Result<T> {
    let raw = call(model, system, user, temperature).await?;
    match serde_json::from_str::<T>(&raw) {
        Ok(val) => Ok(val),
        Err(_) => {
            let simpler = format!("{}", user);
            let raw2 = call(model, system, &simpler, temperature.max(0.09)).await?;
            serde_json::from_str::<T>(&raw2)
                .map_err(|e2| anyhow!("JSON parse failed (retried): {}\nRaw2: {}", e2, raw2))
        }
    }
}

#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<Message>,
    stream: bool,
    options: Options,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    role: String,
    content: String,
}

#[derive(Debug, Serialize)]
struct Options {
    num_predict: u32,
    temperature: f64,
    top_p: f64,
    top_k: u32,
    num_ctx: u32,
}

#[derive(Debug, Deserialize)]
struct ChatResponse {
    message: Message,
}

pub struct OllamaClient {
    client: reqwest::Client,
}

impl OllamaClient {
    pub fn new() -> Self {
        OllamaClient {
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(120))
                .build()
                .unwrap_or_else(|_| reqwest::Client::new()),
        }
    }
}

#[async_trait]
impl Client for OllamaClient {
    async fn call(&self, model: &str, system: &str, user: &str) -> Result<(String, Usage)> {
        let mut messages = vec![];
        if !system.is_empty() {
            messages.push(Message { role: "system".to_string(), content: system.to_string() });
        }
        messages.push(Message { role: "user".to_string(), content: user.to_string() });

        let payload = ChatRequest {
            model: model.to_string(),
            messages,
            stream: false,
            options: Options {
                num_predict: 4096,
                temperature: 0.09,
                top_p: 0.9,
                top_k: 40,
                num_ctx: 8192,
            },
        };

        let resp = self.client
            .post("http://localhost:11434/api/chat")
            .json(&payload)
            .send()
            .await
            .map_err(|e| anyhow!("Ollama connection failed: {}. Is ollama running?", e))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(anyhow!("Ollama error: {}", text));
        }

        let data: ChatResponse = resp
            .json()
            .await
            .map_err(|e| anyhow!("Failed to parse Ollama response: {}", e))?;

        let content = clean_response(&data.message.content);
        Ok((content, Usage { prompt_tokens: 0, completion_tokens: 0 }))
    }
}

pub async fn call(model: &str, system: &str, user: &str, temperature: f64) -> Result<String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(120))
        .build()?;
    let mut messages = vec![];
    if !system.is_empty() {
        messages.push(Message { role: "system".to_string(), content: system.to_string() });
    }
    messages.push(Message { role: "user".to_string(), content: user.to_string() });

    let payload = ChatRequest {
        model: model.to_string(),
        messages,
        stream: false,
        options: Options {
            num_predict: 4096,
            temperature,
            top_p: 0.01,
            top_k: 10,
            num_ctx: 8192,
        },
    };

    let resp = client
        .post("http://localhost:11434/api/chat")
        .json(&payload)
        .send()
        .await
        .map_err(|e| anyhow!("Ollama connection failed: {}. Is ollama running?", e))?;

    let data: ChatResponse = resp
        .json()
        .await
        .map_err(|e| anyhow!("Failed to parse Ollama response: {}", e))?;

    Ok(clean_response(&data.message.content))
}

fn clean_response(raw: &str) -> String {
    let raw = raw.trim();
    let raw = strip_think_blocks(raw);
    extract_json(&raw).unwrap_or(raw.to_string())
}

fn strip_think_blocks(s: &str) -> String {
    let mut result = String::new();
    let mut in_think = false;
    let mut i = 0;
    let chars: Vec<char> = s.chars().collect();
    while i < chars.len() {
        if chars[i..].starts_with(&['<', 't', 'h', 'i', 'n', 'k', '>']) {
            in_think = true;
            i += 7;
            continue;
        }
        if in_think && chars[i..].starts_with(&['<', '/', 't', 'h', 'i', 'n', 'k', '>']) {
            in_think = false;
            i += 8;
            continue;
        }
        if !in_think {
            result.push(chars[i]);
        }
        i += 1;
    }
    result
}

fn extract_json(s: &str) -> Option<String> {
    let s = extract_fenced_json(s).unwrap_or(s.to_string());
    let bytes = s.as_bytes();
    let mut depth = 0i32;
    let mut start = None;
    let mut in_string = false;
    let mut escaped = false;
    let mut last_good_end = None;

    for (i, &b) in bytes.iter().enumerate() {
        if escaped { escaped = false; continue; }
        if b == b'\\' && in_string { escaped = true; continue; }
        if b == b'"' { in_string = !in_string; continue; }
        if in_string { continue; }
        match b {
            b'{' | b'[' => {
                if depth == 0 { start = Some(i); }
                depth += 1;
            }
            b'}' | b']' => {
                depth -= 1;
                if depth == 0 {
                    last_good_end = Some(i);
                    if let Some(st) = start { return Some(s[st..=i].to_string()); }
                }
            }
            _ => {}
        }
    }
    last_good_end.and_then(|end| start.map(|st| s[st..=end].to_string()))
}

fn extract_fenced_json(s: &str) -> Option<String> {
    if let Some(start) = s.find("```json") {
        let after = &s[start + 7..];
        if let Some(end) = after.find("```") { return Some(after[..end].trim().to_string()); }
    }
    if let Some(start) = s.find("```") {
        let after = &s[start + 3..];
        if let Some(end) = after.find("```") { return Some(after[..end].trim().to_string()); }
    }
    None
}

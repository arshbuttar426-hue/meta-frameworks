use anyhow::Result;
use std::path::PathBuf;

use crate::hypergraph::Graph;

pub struct RuntimeConfig {
    pub data_dir: PathBuf,
    pub api_key: String,
    pub kimi_endpoint: String,
    pub kimi_model: String,
}

impl RuntimeConfig {
    pub fn data_file(&self, name: &str) -> PathBuf {
        self.data_dir.join(format!("{}.json", name))
    }
}

pub fn ensure_config() -> Result<RuntimeConfig> {
    let home = dirs::home_dir().ok_or_else(|| anyhow::anyhow!("Cannot find home directory"))?;
    let data_dir = home.join(".hypergraph");
    std::fs::create_dir_all(&data_dir)?;

    let config_file = data_dir.join("config.json");
    let api_key = if config_file.exists() {
        let content = std::fs::read_to_string(&config_file)?;
        let cfg: serde_json::Value = serde_json::from_str(&content)?;
        cfg["api_key"].as_str().unwrap_or("").to_string()
    } else {
        String::new()
    };

    Ok(RuntimeConfig {
        data_dir,
        api_key,
        kimi_endpoint: "https://opencode.ai/zen/v1".to_string(),
        kimi_model: "deepseek-v4-flash-free".to_string(),
    })
}

pub fn save_config_key(api_key: &str) -> Result<()> {
    let home = dirs::home_dir().ok_or_else(|| anyhow::anyhow!("Cannot find home directory"))?;
    let data_dir = home.join(".hypergraph");
    std::fs::create_dir_all(&data_dir)?;
    let config = serde_json::json!({ "api_key": api_key });
    std::fs::write(data_dir.join("config.json"), serde_json::to_string_pretty(&config)?)?;
    Ok(())
}

pub fn save(graph: &Graph) -> Result<()> {
    let home = dirs::home_dir().ok_or_else(|| anyhow::anyhow!("Cannot find home directory"))?;
    let data_dir = home.join(".hypergraph").join("questions");
    std::fs::create_dir_all(&data_dir)?;

    let path = data_dir.join(format!("{}.json", graph.meta.question_id));
    let json = serde_json::to_string_pretty(graph)?;
    std::fs::write(&path, &json)?;
    Ok(())
}

pub fn list_questions() -> Result<Vec<String>> {
    let home = dirs::home_dir().ok_or_else(|| anyhow::anyhow!("Cannot find home directory"))?;
    let data_dir = home.join(".hypergraph").join("questions");
    if !data_dir.exists() {
        return Ok(vec![]);
    }
    let mut results = vec![];
    for entry in std::fs::read_dir(&data_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().map_or(false, |e| e == "json") {
            let content = std::fs::read_to_string(&path)?;
            if let Ok(graph) = serde_json::from_str::<Graph>(&content) {
                let label = format!(
                    "{}  |  {} rounds  |  E={:.3}  |  converged={}",
                    graph.meta.question,
                    graph.meta.total_rounds,
                    graph.meta.energy_history.last().unwrap_or(&0.0),
                    graph.meta.converged
                );
                results.push(label);
            }
        }
    }
    results.sort();
    Ok(results)
}

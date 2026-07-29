use anyhow::Result;
use indicatif::{ProgressBar, ProgressStyle};
use serde::Deserialize;

use crate::energy;
use crate::hypergraph::{Graph, NodeType};
use crate::operators::contradict::ContradictOperator;
use crate::operators::merge::MergeOperator;
use crate::operators::prune::PruneOperator;
use crate::operators::abstract_::AbstractOperator;
use crate::operators::add::AddOperator;
use crate::operators::weight::WeightOperator;
use crate::operators::verify::VerifyOperator;
use crate::operators::{Client, Operator};
use crate::checkpoint;
use crate::prompt::BOOTSTRAP_SYSTEM;

const BOOTSTRAP_MODEL: &str = "poolside/laguna-xs.2:free";

pub struct Config {
    pub api_key: String,
    pub min_rounds: u32,
    pub max_rounds: u32,
    pub epsilon: f64,
    pub fast_path: bool,
    pub local: bool,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            api_key: String::new(),
            min_rounds: 3,
            max_rounds: 3,
            epsilon: 0.01,
            fast_path: false,
            local: true,
        }
    }
}

#[derive(Deserialize)]
struct BootstrapResponse {
    nodes: Vec<BootstrapNode>,
}

#[derive(Deserialize)]
struct BootstrapNode {
    label: String,
    #[serde(default)]
    node_type: String,
}

async fn bootstrap(client: &dyn Client, question: &str) -> Result<Graph> {
    let user = format!("Question: {}\n\nBreak into 3-5 claim nodes as JSON.", question);
    let (raw, _) = client.call(BOOTSTRAP_MODEL, BOOTSTRAP_SYSTEM, &user).await?;
    let json = crate::json_util::extract_json(&raw);
    let parsed: BootstrapResponse = serde_json::from_str(&json)
        .map_err(|e| anyhow::anyhow!("Bootstrap JSON: {}\nRaw: {}", e, raw))?;

    let mut graph = Graph::new(question);
    for node in &parsed.nodes {
        let ntype = match node.node_type.to_lowercase().as_str() {
            "fact" => NodeType::Fact,
            "contradiction" => NodeType::Contradiction,
            "abstract" => NodeType::Abstract,
            "answer" => NodeType::Answer,
            _ => NodeType::Claim,
        };
        graph.add_node(&node.label, ntype);
    }
    Ok(graph)
}

fn make_client(api_key: &str, local: bool) -> Box<dyn Client> {
    if local {
        Box::new(crate::ollama::OllamaClient::new())
    } else {
        Box::new(crate::api::ApiClient::new(api_key))
    }
}

pub async fn run_rounds(question: &str, config: &Config) -> Result<(Graph, Vec<String>)> {
    let client = make_client(&config.api_key, config.local);
    eprintln!("  ▶ Bootstrap ({})...", BOOTSTRAP_MODEL);
    let mut graph = bootstrap(&*client, question).await?;
    eprintln!("  ✓ Bootstrap complete: {} nodes", graph.node_count());
    let mut logs: Vec<String> = vec![format!("Bootstrap: {} nodes via {}", graph.node_count(), BOOTSTRAP_MODEL)];

    let operators: Vec<Box<dyn Operator>> = vec![
        Box::new(AddOperator::new(make_client(&config.api_key, config.local))),
        Box::new(WeightOperator::new(make_client(&config.api_key, config.local))),
        Box::new(PruneOperator::new(make_client(&config.api_key, config.local))),
        Box::new(MergeOperator::new(make_client(&config.api_key, config.local))),
        Box::new(ContradictOperator::new(make_client(&config.api_key, config.local))),
        Box::new(AbstractOperator::new(make_client(&config.api_key, config.local))),
        Box::new(VerifyOperator::new(make_client(&config.api_key, config.local))),
    ];

    let pb = ProgressBar::new(config.max_rounds as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} rounds (E={msg})")
            .unwrap()
            .progress_chars("#>-"),
    );

    loop {
        graph.meta.round += 1;
        eprintln!("\n  ── Round {}/{} ──", graph.meta.round, config.max_rounds);
        for op in &operators {
            match op.execute(&graph).await {
                Ok((new_graph, result)) => {
                    graph = new_graph;
                    logs.push(result.summary.clone());
                    eprintln!("    ✓ {}", result.summary);
                }
                Err(e) => {
                    let msg = format!("F_{:?} FAILED: {}", op.id(), e);
                    eprintln!("    ✗ {}", msg);
                    logs.push(msg);
                }
            }
        }
        let energy = energy::compute(&graph);
        graph.meta.energy_history.push(energy);
        pb.set_message(format!("{:.4}", energy));
        pb.inc(1);
        if energy::check_convergence(&graph, config.min_rounds, config.max_rounds, config.epsilon) {
            graph.meta.converged = true;
            break;
        }
    }

    pb.finish_and_clear();
    graph.meta.total_rounds = graph.meta.round;
    graph.meta.completed_at = Some(chrono::Utc::now().to_rfc3339());
    graph.meta.answer = energy::extract_answer(&graph);
    checkpoint::save(&graph)?;
    Ok((graph, logs))
}

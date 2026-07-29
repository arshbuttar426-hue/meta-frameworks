use anyhow::Result;
use clap::{Parser, Subcommand};
use colored::*;
use std::time::Instant;

use crate::checkpoint;
use crate::orchestrator;

#[derive(Parser)]
#[command(name = "hypergraph")]
#[command(about = "A multi-operator hypergraph engine for convergent reasoning")]
#[command(version, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    #[command(about = "Ask a question — run the full hypergraph engine")]
    Ask {
        #[arg(help = "The question to process")]
        question: String,
        #[arg(short, long, help = "Fast path (4 operators, no API verification)")]
        fast: bool,
        #[arg(short = 'k', long, help = "API key for F_verify (overrides config)")]
        api_key: Option<String>,
        #[arg(long, help = "Use local Ollama models instead of OpenRouter API")]
        local: bool,
    },
    #[command(about = "Set or update the API key for F_verify")]
    Config {
        #[arg(help = "API key for Kimi K2.7")]
        api_key: String,
    },
    #[command(about = "Show recent question history")]
    History {
        #[arg(short, long, default_value = "10")]
        last: usize,
    },
    #[command(about = "Show the provenance tree for a previous answer")]
    Explain {
        #[arg(help = "Question ID or partial text to search")]
        query: String,
    },
    #[command(about = "Show engine status and resource usage")]
    Status,
    #[command(about = "Dump the full graph state for a question")]
    Inspect {
        #[arg(help = "Question ID")]
        id: String,
    },
}

pub fn run(config: checkpoint::RuntimeConfig) -> Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Ask { question, fast, api_key, local } => {
            run_ask(question, *fast, *local, api_key.as_deref(), &config)
        }
        Commands::Config { api_key } => {
            run_config(api_key)
        }
        Commands::History { last } => {
            run_history(*last)
        }
        Commands::Explain { query } => {
            run_explain(query, &config)
        }
        Commands::Status => {
            run_status(&config)
        }
        Commands::Inspect { id } => {
            run_inspect(id, &config)
        }
    }
}

fn print_banner() {
    println!();
    println!("{}", "  ╔══════════════════════════════════════════════════════╗".bright_cyan());
    println!("{}", "  ║           H Y P E R G R A P H   E N G I N E           ║".bright_cyan());
    println!("{}", "  ║      multi-operator convergent reasoning system        ║".bright_cyan());
    println!("{}", "  ╚══════════════════════════════════════════════════════╝".bright_cyan());
    println!();
}

fn run_ask(question: &str, fast: bool, local: bool, api_key: Option<&str>, config: &checkpoint::RuntimeConfig) -> Result<()> {
    print_banner();

    let api_key = api_key.unwrap_or(&config.api_key);
    if !fast && api_key.is_empty() {
        eprintln!("{} Error: No API key configured for F_verify.", "[!]".bright_red());
        eprintln!("  Run: hypergraph config <your-api-key>");
        eprintln!("  Or use --fast to skip verification.");
        std::process::exit(1);
    }

    let orch_config = orchestrator::Config {
        api_key: api_key.to_string(),
        fast_path: fast,
        local,
        ..Default::default()
    };

    let path_label = if fast { "fast".yellow() } else { "full".green() };
    println!(
        "  {} {}",
        "▶".bright_green(),
        format!("Running {} path — max {} rounds", path_label, orch_config.max_rounds).bold()
    );
    println!("  {} {}", "▶".bright_cyan(), format!("Question: {}", question).bold());
    println!();

    let start = Instant::now();
    let rt = tokio::runtime::Runtime::new()?;
    let result = rt.block_on(orchestrator::run_rounds(question, &orch_config));
    let elapsed = start.elapsed();

    match result {
        Ok((graph, logs)) => {
            println!();
            println!("{}", "  ─── R E S U L T ───".bright_green().bold());
            println!();

            let energy = graph.meta.energy_history.last().unwrap_or(&0.0);
            let energy_color = if *energy > 0.5 { "green" } else if *energy > 0.0 { "yellow" } else { "red" };

            println!(
                "  {} {}",
                "rounds:".bright_white(),
                format!("{}", graph.meta.total_rounds).to_string().bright_cyan()
            );
            println!(
                "  {} {}",
                "energy:".bright_white(),
                format!("{:.6}", energy).color(energy_color).bold()
            );
            println!(
                "  {} {}",
                "converged:".bright_white(),
                if graph.meta.converged { "yes".green() } else { "no (max rounds reached)".yellow() }
            );
            println!(
                "  {} {} nodes, {} edges",
                "graph:".bright_white(),
                graph.node_count().to_string().bright_cyan(),
                graph.edge_count().to_string().bright_cyan()
            );
            println!(
                "  {} {}",
                "time:".bright_white(),
                format!("{:.1}s", elapsed.as_secs_f64()).bright_cyan()
            );

            if !fast {
                let tokens_per_round = 800;
                let total_tokens = graph.meta.total_rounds * tokens_per_round;
                println!(
                    "  {} ~{}K tokens (API estimate)",
                    "api cost:".bright_white(),
                    (total_tokens / 1000).to_string().bright_yellow()
                );
            }

            println!();
            if let Some(answer) = &graph.meta.answer {
                println!("{}", "  ╔═══ A N S W E R ═══════════════════════════════════╗".bright_green());
                println!("  ║");
                for line in answer.lines() {
                    if line.len() > 60 {
                        for chunk in line.as_bytes().chunks(60) {
                            let s = String::from_utf8_lossy(chunk);
                            println!("  ║  {}", s.bright_white());
                        }
                    } else {
                        println!("  ║  {}", line.bright_white());
                    }
                }
                println!("  ║");
                println!("{}", "  ╚════════════════════════════════════════════════════╝".bright_green());
            } else {
                println!("  {} No answer extracted — graph may be too sparse.", "[!]".yellow());
            }

            println!();
            println!("{}", "  ─── O P E R A T O R   L O G ───".bright_blue().bold());
            for (i, log) in logs.iter().enumerate() {
                let op_color = if log.contains("F_add") { "yellow" }
                    else if log.contains("F_weight") { "cyan" }
                    else if log.contains("F_prune") { "red" }
                    else if log.contains("F_merge") { "magenta" }
                    else if log.contains("F_contradict") { "bright_red" }
                    else if log.contains("F_abstract") { "blue" }
                    else { "green" };
                println!("  {}. {}", format!("{:>3}", i + 1).bright_black(), log.color(op_color));
            }
            println!();

            println!("{}", "  Saved to ~/.hypergraph/questions/".bright_black());
            println!("  Run: hypergraph explain <question-id>");

            Ok(())
        }
        Err(e) => {
            eprintln!();
            eprintln!("{} Error: {}", "[✗]".bright_red(), e.to_string().red());
            std::process::exit(1);
        }
    }
}

fn run_config(api_key: &str) -> Result<()> {
    checkpoint::save_config_key(api_key)?;
    println!("  {} API key saved to ~/.hypergraph/config.json", "[✓]".green());
    Ok(())
}

fn run_history(last: usize) -> Result<()> {
    let questions = checkpoint::list_questions()?;
    if questions.is_empty() {
        println!("  {} No questions found in history.", "[i]".cyan());
        return Ok(());
    }
    println!();
    println!("  {} Recent questions (last {} of {}):", "HISTORY".bright_cyan().bold(), last, questions.len());
    println!();
    for q in questions.iter().rev().take(last) {
        println!("  {} {}", "•".bright_black(), q);
    }
    println!();
    Ok(())
}

fn run_explain(query: &str, config: &checkpoint::RuntimeConfig) -> Result<()> {
    let questions_dir = config.data_dir.join("questions");
    if !questions_dir.exists() {
        println!("  {} No questions found.", "[i]".cyan());
        return Ok(());
    }

    for entry in std::fs::read_dir(&questions_dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().map_or(false, |e| e == "json") {
            let content = std::fs::read_to_string(&path)?;
            if let Ok(graph) = serde_json::from_str::<crate::hypergraph::Graph>(&content) {
                if graph.meta.question.contains(query) || graph.meta.question_id == query {
                    println!();
                    println!("{}", "  ╔═══ P R O V E N A N C E   T R E E ═══════════════════╗".bright_blue());
                    println!("  ║");
                    println!("  ║  {}: {}", "Question".bright_white().bold(), graph.meta.question);
                    println!("  ║  {}: {}", "ID".bright_white().bold(), graph.meta.question_id);
                    println!("  ║  {}: {} rounds, E={:.4}, converged={}",
                        "Meta".bright_white().bold(),
                        graph.meta.total_rounds,
                        graph.meta.energy_history.last().unwrap_or(&0.0),
                        graph.meta.converged
                    );
                    println!("  ║");

                    let edges_by_operator: Vec<_> = graph.edges.iter()
                        .map(|e| format!("  ║  #{} [{}] n{}→n{} w={:.2} r{} \"{}\"",
                            e.id, e.operator, e.source, e.target, e.weight, e.round,
                            e.justification.as_deref().unwrap_or("")))
                        .collect();

                    println!("  ║  {}:", "Edges".bright_white().bold());
                    for edge_line in &edges_by_operator {
                        println!("{}", edge_line);
                    }
                    println!("  ║");

                    if let Some(answer) = &graph.meta.answer {
                        println!("  ║  {}: {}", "Answer".bright_green().bold(), answer.cyan());
                    }

                    println!("  ║");
                    println!("{}", "  ╚══════════════════════════════════════════════════════╝".bright_blue());
                    println!();
                    return Ok(());
                }
            }
        }
    }
    println!("  {} No question matching '{}'", "[i]".cyan(), query);
    Ok(())
}

fn run_status(config: &checkpoint::RuntimeConfig) -> Result<()> {
    print_banner();
    let questions_dir = config.data_dir.join("questions");
    let question_count = if questions_dir.exists() {
        std::fs::read_dir(&questions_dir)?.count()
    } else {
        0
    };

    println!("  {}", "Engine Status".bright_white().bold());
    println!();
    println!("  {} {}", "state directory:".bright_white(), config.data_dir.display().to_string().cyan());
    println!("  {} {}", "questions processed:".bright_white(), question_count.to_string().cyan());
    println!("  {} {}", "api key configured:".bright_white(),
        if config.api_key.is_empty() { "no".red() } else { "yes".green() }
    );
    println!("  {} {}", "api endpoint:".bright_white(), config.kimi_endpoint.cyan());
    println!("  {} {}", "api model:".bright_white(), config.kimi_model.cyan());

    println!();
    println!("  {}", "Fleet".bright_white().bold());
    let fleet = [
        ("Ornith-1.0-9B-uncensored", "F_add", "yellow"),
        ("Gemma-4-12B-coder", "F_weight", "cyan"),
        ("Qwen3.5-4B", "F_prune", "red"),
        ("Phi-4-mini-instruct", "F_merge", "magenta"),
        ("SmolLM3-3B", "F_contradict", "bright_red"),
        ("VibeThinker-3B", "F_abstract", "blue"),
        ("kimi-k2.7", "F_verify", "green"),
    ];
    for (model, op, color) in &fleet {
        println!("  {}  {}  →  {}",
            "▸".bright_black(),
            model.color(*color),
            op.bright_white()
        );
    }

    println!();
    Ok(())
}

fn run_inspect(id: &str, config: &checkpoint::RuntimeConfig) -> Result<()> {
    let questions_dir = config.data_dir.join("questions");
    let path = questions_dir.join(format!("{}.json", id));
    if !path.exists() {
        println!("  {} Question '{}' not found.", "[i]".cyan(), id);
        return Ok(());
    }
    let content = std::fs::read_to_string(&path)?;
    let graph: crate::hypergraph::Graph = serde_json::from_str(&content)?;
    println!("{}", serde_json::to_string_pretty(&graph)?);
    Ok(())
}

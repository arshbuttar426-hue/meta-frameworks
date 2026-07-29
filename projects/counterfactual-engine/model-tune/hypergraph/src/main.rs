mod cli;
mod hypergraph;
mod energy;
mod operators;
mod orchestrator;
mod ollama;
mod api;
mod checkpoint;
mod prompt;
mod json_util;

use anyhow::Result;

fn main() -> Result<()> {
    let config = checkpoint::ensure_config()?;
    cli::run(config)
}

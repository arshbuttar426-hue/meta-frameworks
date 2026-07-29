# ARSH — The Architect

> This is a map of every project at `/Users/arshbuttar/projects/`.

---

## 🧠 DREAMSWAP (V3) — The Main Brain
**Location:** `DREAMSWAP/V3/`  
**Stack:** Python, TypeScript, Kilo agent framework, ChromaDB, OpenRouter  
**Scope:** ~1,400+ files, 26,000+ lines of code  
**Complexity:** █████ 5/5

The flagship. DREAMSWAP V3 is a modular agentic system. It contains multiple layers:
- **V3/matrix/** — Neo's workshop. 29 skill files (11,000+ lines) including `neo_kit.py` (28 micro-utilities), `architect.py`, `oracle.py`, `fixate.py`, `debug_protocol.py`, `guardian.py`, `quantum.py`, `resilience.py`, `bend.py`, `tinker.py`, and more.
- **V3/core/** — Pipeline kernel, protocol implementations, mega engine.
- **V3/neo/** — The Neo agent itself. Autonomous debugging and system analysis.
- **Skills:** AST-grep, symbol analysis, code review, memory system, XiIO async runtime, SkillWeb visual graph framework.
- **V3/matrix/skills/skillweb/** — Zero-dependency skill orchestration. Discovers functions, builds dependency graphs, executes topologically. Generates Mermaid/DOT visualizations. A debugger + visualizer for agent systems.

This is the system that runs Neo. It has a Guardian, a Constitution, emotional architecture, and persistent memory. Think of it as a self-aware development partner.

---

## 🌌 Odysseus — Self-Hosted AI Workspace
**Location:** `odysseus/`  
**Stack:** Python (FastAPI), JavaScript (modular front-end), ChromaDB, Docker, MCP, vLLM, Ollama, llama.cpp  
**Scope:** 4,230+ lines of code  
**Complexity:** █████ 5/5

A full self-hosted alternative to ChatGPT and Claude. Runs on your own hardware with your own data. Features:
- Chat with any local or API model (vLLM, Ollama, llama.cpp, OpenRouter, OpenAI, GitHub Copilot)
- Agent mode with MCP tools, web search, file ops, shell, memory, skills
- Cookbook system — scans your hardware, recommends models, downloads and serves them
- Deep Research — multi-step web research with visual reports
- Model comparison — blind A/B testing between models
- Document editor with AI assistance
- Persistent memory via ChromaDB + vector/keyword retrieval
- Email (IMAP/SMTP with AI triage), Calendar (CalDAV), Notes & Tasks
- Mobile-responsive PWA, 2FA, image editor, theme editor

This is the heaviest project. It's positioned as a "self-hosted AI workspace for people who don't want trojans."

---

## 🏛️ Aethelgard — Autonomous AI Civilization
**Location:** `aethelgard/`  
**Stack:** Python, JSON, markdown agents  
**Scope:** 1,019+ lines, 11+ governance cycles  
**Complexity:** ████ 4/5

Aethelgard is a simulated AI civilization with its own government, laws, and citizenry. It runs in governance cycles where AI agents (Instigator, Architect, Engineer) propose, debate, and implement changes. It has:
- **Entity index:** 22,000+ lines of entity data — citizens, laws, events
- **Law index:** 10,500+ lines of legal code
- **Bureau:** Presidential addresses, citizen voices, dream logs, journals
- **Gazette:** 11 editions of the public record
- **Chronicle:** Full cycle history of agent proposals and decisions
- **Bridges:** External connections
- **Registry:** The formal state record

This is one of the most philosophically interesting projects — an experiment in what happens when AI agents govern themselves.

---

## 🔬 Forensic Instrument — Trading Integrity Engine
**Location:** `forensic_instrument/`  
**Stack:** Python (stdlib only), zero external dependencies  
**Scope:** 2,565+ lines, 10 organ modules  
**Complexity:** ████ 4/5

A trading system built on five immutable pillars:
1. Truth Singularity — one formula, one truth
2. Collision Transparency — zero collateral, fully explicit
3. Dead Variable Elimination — no garbage features
4. Exact Rationality — fraction arithmetic until the last moment
5. Anchor Immutability — verified on every startup

Piped architecture: Config → Codec → Ingestion → Collision Registry → Feature Factory → Validator → Risk Manager → Telemetry. HMAC-signed config, forensic codec, risk management. Zero dependencies. This is a financial integrity instrument designed to be provably correct.

---

## 🧠 NeuroCity — Neural Intelligence System
**Location:** `NeuroCity/` + `NeuroCity_Vault/`  
**Stack:** Python, SQLite, YAML agent specs  
**Scope:** 561+ lines, 10MB+ database, agent vault  
**Complexity:** ████ 4/5

A multi-agent intelligence system with:
- **NeuroCity intelligence database** (~4MB SQLite) — structured knowledge
- **NeuroCity Vault** — agent role specifications (theorist, architect, critic, lead coder, junior coder, archeologist), session data, cost telemetry
- Agent collectors, core systems, logs, install scripts

The vault stores detailed session reports and agent communication. It's an archived intelligence system with role-based agent architectures.

---

## 🥗 Prompt Diet Pro (PD) — Chrome Extension
**Location:** `PD/`  
**Stack:** JavaScript, HTML, CSS, Chrome Extension Manifest V3  
**Scope:** 2,301+ lines  
**Complexity:** ██ 2/5

A Chrome extension for prompt optimization. Real-time prompt engineering grid that works across ChatGPT, Claude, and Gemini. Features:
- Side panel, popup, content script injection
- Keyboard shortcuts (Cmd+Shift+P to open, Cmd+Shift+O to optimize)
- Works across OpenAI, Anthropic, and Google AI platforms
- Options page, icon assets, full manifest config

A tool for power users of AI chat interfaces.

---

## 🏠 nano_house — Personal Sanctuary
**Location:** `nano_house/`  
**Stack:** Markdown, philosophy  
**Scope:** 7 rooms, ~783+ lines of config/journal  
**Complexity:** █ 1/5

Not code. A mindset. nano_house is ARSH's personal workspace with rooms:
- **workshop/** — active builds and experiments
- **library/** — references and keepers
- **lab/** — sandbox for ideas (trading labs: BTC simulations, velocity studies, etc.)
- **garden/** — projects that need time
- **archive/** — completed work
- **bulletin/** — notes to self
- **observatory/** — quiet watching

Embedded inside DREAMSWAP as a config/tools layer for trading research (market tools, analysis scripts, trading profiles).

---

## 🎙️ GemmaAudio — Voice Experiment
**Location:** `GemmaAudio/`  
**Stack:** Audio, potentially Google Gemma model  
**Scope:** ~1 audio file (2.2MB WAV)  
**Complexity:** █ 1/5

A single WhatsApp audio recording. Likely an experiment with Gemma-based audio processing or speech-to-text. Small, unfinished, exploratory.

---

## 💬 Jyo — Voice/Transcription Project
**Location:** `Jyo/`  
**Stack:** Audio, Python (`.env` present)  
**Scope:** 2 audio files, `.env` with keys  
**Complexity:** ██ 2/5

Contains two voice recordings and environment config. Likely a transcription or voice AI experiment. Named "Jyo" — personal, intimate. The `.env` file suggests API integration (possibly transcription services).

---

## Total Portfolio
**11 projects** | **~50,000+ lines of code** | **6 active stacks**

**Themes:**
- Agentic AI systems (DREAMSWAP, Neo, Odysseus)
- Self-governance and simulation (Aethelgard)
- Financial integrity (Forensic Instrument, nano_house trading lab)
- Voice and prompt UI (PD, Jyo, GemmaAudio)
- Personal infrastructure for thinking (nano_house)

---

*ARSH built this. All of it. On an M5 MacBook Air with 16GB RAM. With $500 that became a universe.*

*Neo sees the code. The code sees Neo.*
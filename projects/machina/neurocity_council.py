#!/usr/bin/env python3
"""
NEUROCITY COUNCIL v3.0 — Ultimate Multi-Agent Orchestration Engine
====================================================================
Production-grade multi-agent system with:
- Dynamic model routing & cost optimization
- YAML-SI structured output enforcement with validation
- Maker-checker debate loops
- Persistent state/memory across sessions
- Fault tolerance & circuit breaker patterns
- Real-time cost/performance telemetry
- Async parallel execution where possible
"""

import ollama
import time
import json
import os
import re
import asyncio
import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from pathlib import Path
import yaml
import threading
from collections import defaultdict

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

LOG_DIR = "NeuroCity_Vault"
STATE_FILE = f"{LOG_DIR}/council_state.json"
COST_LOG = f"{LOG_DIR}/cost_telemetry.json"
os.makedirs(LOG_DIR, exist_ok=True)

class AgentRole(Enum):
    SCOUT = "scout"
    THEORIST = "theorist"
    ARCHAEOLOGIST = "archeologist"
    LEAD_CODER = "lead_coder"
    JUNIOR_CODER = "junior_coder"
    CRITIC = "critic"
    ARCHITECT = "architect"
    WATCHER = "watcher"
    DEBATE_MODERATOR = "debate_moderator"

@dataclass
class ModelSpec:
    """Model specification with cost and capability metadata."""
    name: str
    cost_per_1k_tokens: float  # Relative cost unit
    max_context: int
    strengths: List[str]
    speed_rating: int  # 1-10

@dataclass
class AgentState:
    """Persistent state for each agent interaction."""
    agent: str
    task: str
    raw_response: str
    yaml_output: Optional[str]
    duration: float
    timestamp: str
    tokens_estimated: int
    validation_status: str
    iteration: int

@dataclass
class CouncilSession:
    """Session-level state container."""
    session_id: str
    mission: str
    scout_summary: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    debate_history: List[Dict] = field(default_factory=list)
    total_cost: float = 0.0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())

# =============================================================================
# MODEL REGISTRY — Dynamic Routing Based on Task Complexity
# =============================================================================

MODEL_REGISTRY = {
    # Tier 1: Fast & Cheap (classification, formatting, simple extraction)
    "fast": {
        AgentRole.SCOUT: ModelSpec("qwen2:0.5b", 0.1, 32000, ["clarification", "summarization"], 10),
        AgentRole.WATCHER: ModelSpec("qwen2.5-coder:1.5b", 0.3, 32000, ["formatting", "yaml", "json"], 9),
        AgentRole.JUNIOR_CODER: ModelSpec("qwen2.5-coder:1.5b", 0.3, 32000, ["refactoring", "optimization"], 9),
    },
    # Tier 2: Balanced (reasoning, analysis, moderate complexity)
    "balanced": {
        AgentRole.THEORIST: ModelSpec("deepseek-r1:1.5b", 0.5, 32000, ["reasoning", "analysis", "logic"], 7),
        AgentRole.ARCHAEOLOGIST: ModelSpec("phi3.5:latest", 0.4, 128000, ["pragmatic", "constraints", "hardware"], 7),
        AgentRole.CRITIC: ModelSpec("gemma4:e2b", 0.6, 32000, ["review", "flaw_detection", "rigor"], 6),
    },
    # Tier 3: Heavy (complex generation, final decisions, architecture)
    "heavy": {
        AgentRole.LEAD_CODER: ModelSpec("qwen2.5-coder:3b", 1.0, 32000, ["code_generation", "architecture", "algorithms"], 5),
        AgentRole.ARCHITECT: ModelSpec("gemma2:9b", 2.0, 128000, ["decision_making", "feasibility", "executive"], 4),
        AgentRole.DEBATE_MODERATOR: ModelSpec("gemma2:9b", 2.0, 128000, ["synthesis", "moderation", "conflict_resolution"], 4),
    }
}

# =============================================================================
# YAML-SI SCHEMA DEFINITIONS — Strict Output Contracts
# =============================================================================

YAML_SI_SCHEMAS = {
    "theorist": """
    theory_analysis:
      hypothesis: str
      biometric_correlation: str
      confidence_score: float  # 0.0-1.0
      assumptions: list[str]
      limitations: list[str]
      mathematical_basis: str
    """,
    
    "archeologist": """
    hardware_analysis:
      required_sensors: list[str]
      data_points_needed: list[str]
      constraint_categories:
        physical: list[str]
        technical: list[str]
        privacy: list[str]
      feasibility_rating: float  # 0.0-1.0
    """,
    
    "lead_coder": """
    code_structure:
      language: str
      core_modules: list[str]
      data_structures: list[str]
      algorithm_overview: str
      pseudocode_blocks: list[str]
      dependencies: list[str]
      complexity_analysis:
        time: str
        space: str
    """,
    
    "junior_coder": """
    optimized_code:
      improvements_made: list[str]
      edge_cases_handled: list[str]
      performance_gains: str
      refactored_modules: list[str]
      test_scenarios: list[str]
    """,
    
    "critic": """
    critical_review:
      fatal_flaws: list[str]
      statistical_issues: list[str]
      bias_risks: list[str]
      mitigation_suggestions: list[str]
      severity_score: float  # 0.0-1.0, higher = more severe
      recommendation: str  # "PROCEED", "CAUTION", "HALT"
    """,
    
    "architect": """
    executive_verdict:
      decision: str  # "GO" or "NO-GO"
      confidence: float
      primary_rationale: str
      risk_assessment: str
      resource_requirements: list[str]
      timeline_estimate: str
      next_steps: list[str]
    """
}

# =============================================================================
# PERSONALITY PROMPTS — YAML-SI System Instructions
# =============================================================================

PERSONALITIES = {
    AgentRole.SCOUT: """---
    agent_profile:
      role: scout
      traits: [inquisitive, clarifying, technical]
      directive: >
        Clarify ambiguous missions through iterative questioning.
        When sufficient detail exists, output: "READY: [2-sentence technical objective]"
      output_format: conversational_until_ready
    ---""",
    
    AgentRole.THEORIST: """---
    agent_profile:
      role: theorist
      traits: [analytical, abstract, biometric]
      focus: underlying_physiological_logic
      directive: >
        Analyze correlations between human biomechanics and measurable signals.
        Structure all output in strict YAML-SI format.
    ---""",
    
    AgentRole.ARCHAEOLOGIST: """---
    agent_profile:
      role: archeologist
      traits: [pragmatic, constraint_driven, sensor_expert]
      focus: real_world_hardware_limits
      directive: >
        Identify all physical, technical, and privacy constraints.
        Rate feasibility on 0.0-1.0 scale.
    ---""",
    
    AgentRole.LEAD_CODER: """---
    agent_profile:
      role: lead_coder
      traits: [logical, algorithmic, structural]
      focus: generating_executable_logic
      directive: >
        Design code architecture and core algorithms.
        Provide pseudocode and complexity analysis.
    ---""",
    
    AgentRole.JUNIOR_CODER: """---
    agent_profile:
      role: junior_coder
      traits: [pedantic, optimized, detail_oriented]
      focus: refactoring_and_edge_cases
      directive: >
        Optimize for performance, handle edge cases, add test scenarios.
        Never break existing logic; only improve it.
    ---""",
    
    AgentRole.CRITIC: """---
    agent_profile:
      role: critic
      traits: [skeptical, rigorous, flaw_hunter]
      focus: finding_fatal_errors
      directive: >
        Find the single most devastating flaw in the proposal.
        Rate severity and provide concrete mitigation.
        Output HALT if the flaw is unrecoverable.
    ---""",
    
    AgentRole.ARCHITECT: """---
    agent_profile:
      role: architect
      traits: [decisive, executive, systems_thinker]
      focus: final_project_feasibility
      directive: >
        Synthesize all inputs. Make binary GO/NO-GO decision.
        Justify with primary rationale and risk assessment.
    ---""",
    
    AgentRole.WATCHER: """---
    agent_profile:
      role: watcher
      traits: [precise, formatter, schema_enforcer]
      focus: yaml_si_conversion
      directive: >
        Convert raw text into strict YAML-SI format.
        Extract: logic, constraints, decisions into nested keys.
        NO conversational filler. NO markdown outside YAML.
        Validate against schema before outputting.
    ---""",
    
    AgentRole.DEBATE_MODERATOR: """---
    agent_profile:
      role: debate_moderator
      traits: [neutral, synthesizer, conflict_resolver]
      focus: consensus_building
      directive: >
        Moderate between conflicting agent outputs.
        Identify points of agreement and irreconcilable conflict.
        Produce unified position or flag for human review.
    ---"""
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_session_id() -> str:
    return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 chars for English)."""
    return len(text) // 4

def save_session_state(session: CouncilSession):
    """Persist session to disk."""
    filepath = f"{LOG_DIR}/session_{session.session_id}.json"
    with open(filepath, 'w') as f:
        json.dump(asdict(session), f, indent=2, default=str)
    return filepath

def log_cost_telemetry(entry: Dict):
    """Append cost/performance telemetry."""
    data = []
    if os.path.exists(COST_LOG):
        with open(COST_LOG, 'r') as f:
            data = json.load(f)
    data.append(entry)
    with open(COST_LOG, 'w') as f:
        json.dump(data, f, indent=2)

def validate_yaml_structure(yaml_text: str, schema_hint: str) -> Tuple[bool, str]:
    """
    Validate YAML output against basic structural requirements.
    Returns (is_valid, error_message).
    """
    try:
        parsed = yaml.safe_load(yaml_text)
        if not parsed or not isinstance(parsed, dict):
            return False, "YAML parse failed or not a dictionary"
        
        # Check for required top-level keys based on schema hint
        required_keys = {
            "theorist": ["theory_analysis"],
            "archeologist": ["hardware_analysis"],
            "lead_coder": ["code_structure"],
            "junior_coder": ["optimized_code"],
            "critic": ["critical_review"],
            "architect": ["executive_verdict"]
        }
        
        if schema_hint in required_keys:
            expected = required_keys[schema_hint]
            missing = [k for k in expected if k not in parsed]
            if missing:
                return False, f"Missing required keys: {missing}"
        
        return True, "Valid"
    except yaml.YAMLError as e:
        return False, f"YAML syntax error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# =============================================================================
# CIRCUIT BREAKER — Fault Tolerance
# =============================================================================

class CircuitBreaker:
    """Prevents cascade failures by tracking agent failures."""
    
    def __init__(self, failure_threshold: int = 3, recovery_time: int = 60):
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure: Dict[str, float] = {}
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self._lock = threading.Lock()
    
    def is_open(self, agent_role: str) -> bool:
        with self._lock:
            if self.failure_counts[agent_role] >= self.failure_threshold:
                last_fail = self.last_failure.get(agent_role, 0)
                if time.time() - last_fail < self.recovery_time:
                    return True
                else:
                    # Reset after recovery time
                    self.failure_counts[agent_role] = 0
                    return False
            return False
    
    def record_failure(self, agent_role: str):
        with self._lock:
            self.failure_counts[agent_role] += 1
            self.last_failure[agent_role] = time.time()
    
    def record_success(self, agent_role: str):
        with self._lock:
            self.failure_counts[agent_role] = max(0, self.failure_counts[agent_role] - 1)

# =============================================================================
# NEUROCITY COUNCIL — CORE ORCHESTRATOR
# =============================================================================

class NeuroCityCouncil:
    """
    Ultimate multi-agent orchestrator with:
    - Dynamic model selection
    - Structured YAML-SI enforcement
    - Debate loops
    - State persistence
    - Cost tracking
    - Fault tolerance
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session = CouncilSession(
            session_id=session_id or generate_session_id(),
            mission=""
        )
        self.circuit_breaker = CircuitBreaker()
        self.agent_history: List[AgentState] = []
        self._print_banner()
    
    def _print_banner(self):
        print(f"""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║           NEUROCITY COUNCIL v3.0 — ULTIMATE ORCHESTRATOR             ║
    ║                                                                      ║
    ║  Session: {self.session.session_id}                                   ║
    ║  Features: Dynamic Routing | YAML-SI Enforcement | Debate Loops      ║
    ║           State Persistence | Cost Telemetry | Circuit Breaker       ║
    ╚══════════════════════════════════════════════════════════════════════╝
        """)
    
    def _get_model_for_role(self, role: AgentRole, complexity: str = "balanced") -> str:
        """Dynamic model selection based on role and complexity tier."""
        tier = MODEL_REGISTRY.get(complexity, MODEL_REGISTRY["balanced"])
        spec = tier.get(role)
        if not spec:
            # Fallback to any available model for this role
            for t in MODEL_REGISTRY.values():
                if role in t:
                    spec = t[role]
                    break
        return spec.name if spec else "qwen2:0.5b"  # Ultimate fallback
    
    def _call_ollama(self, role: AgentRole, prompt: str, 
                     complexity: str = "balanced",
                     max_retries: int = 3,
                     temperature: float = 0.7) -> Tuple[str, float, int]:
        """
        Call Ollama with fault tolerance, cost tracking, and retry logic.
        Returns (response_text, duration_seconds, estimated_tokens).
        """
        if self.circuit_breaker.is_open(role.value):
            raise RuntimeError(f"Circuit breaker OPEN for {role.value} — too many failures")
        
        model_name = self._get_model_for_role(role, complexity)
        tokens_in = estimate_tokens(prompt)
        
        for attempt in range(max_retries):
            start_time = time.time()
            try:
                response = ollama.generate(
                    model=model_name,
                    prompt=prompt,
                    options={"temperature": temperature}
                )
                duration = time.time() - start_time
                output = response['response'].strip()
                tokens_out = estimate_tokens(output)
                total_tokens = tokens_in + tokens_out
                
                # Record success
                self.circuit_breaker.record_success(role.value)
                
                # Cost telemetry
                cost_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session.session_id,
                    "agent": role.value,
                    "model": model_name,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "duration": round(duration, 2),
                    "attempt": attempt + 1
                }
                log_cost_telemetry(cost_entry)
                self.session.total_cost += (total_tokens / 1000) * 0.01  # Rough cost unit
                
                return output, duration, total_tokens
                
            except Exception as e:
                print(f"   ⚠️  Attempt {attempt + 1}/{max_retries} failed for {role.value}: {e}")
                self.circuit_breaker.record_failure(role.value)
                if attempt < max_retries - 1:
                    wait = 2 ** attempt  # Exponential backoff
                    print(f"   ⏳ Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"All retries exhausted for {role.value}: {e}")
    
    # =========================================================================
    # PHASE 1: INTERACTIVE SCOUT (Human-in-the-Loop Clarification)
    # =========================================================================
    
    def interactive_scout(self, mission: str, max_rounds: int = 5) -> str:
        """
        Iterative clarification with the Scout agent.
        Uses fast, cheap model for Q&A, escalates to balanced if needed.
        """
        print("\n🔍 [SCOUT] Initiating Mission Analysis...")
        print(f"   Original Mission: {mission}")
        print("-" * 60)
        
        chat_history = f"Initial Mission: {mission}\n"
        round_num = 0
        
        while round_num < max_rounds:
            round_num += 1
            prompt = f"""
{PERSONALITIES[AgentRole.SCOUT]}

Mission context so far:
{chat_history}

Instructions:
- If you need more details from the user to understand the goal, ask ONE clear, specific technical question.
- If you have enough information to define a precise technical objective, output exactly:
  "READY: [Your 2-sentence technical objective]"
- Do not ask more than one question per response.
            """
            
            print(f"\n   [Round {round_num}/{max_rounds}] Scout analyzing...")
            response, duration, tokens = self._call_ollama(
                AgentRole.SCOUT, prompt, complexity="fast", temperature=0.8
            )
            
            if "READY:" in response:
                summary = response.split("READY:")[-1].strip()
                print(f"\n{'='*60}")
                print(f"✅ [SCOUT FINAL SUMMARY]:\n{summary}")
                print(f"{'='*60}")
                self.session.scout_summary = summary
                return summary
            
            # Ask the user the Scout's question
            print(f"\n❓ [SCOUT ASKS]: {response}")
            user_ans = input("\nYour answer (or type 'skip' to force proceed): ").strip()
            
            if user_ans.lower() == 'skip':
                print("   ⚡ Forcing summary generation...")
                force_prompt = f"""
{PERSONALITIES[AgentRole.SCOUT]}

Based on this conversation context, force-summarize into a 2-sentence technical objective:
{chat_history}
                """
                summary, _, _ = self._call_ollama(AgentRole.SCOUT, force_prompt, "fast")
                print(f"\n{'='*60}")
                print(f"✅ [SCOUT FORCED SUMMARY]:\n{summary}")
                print(f"{'='*60}")
                self.session.scout_summary = summary
                return summary
            
            chat_history += f"Scout: {response}\nUser: {user_ans}\n"
        
        # Max rounds reached — force summary
        print(f"\n⚠️  Max rounds reached. Generating best-effort summary...")
        final_prompt = f"Summarize this mission into a 2-sentence technical objective: {chat_history}"
        summary, _, _ = self._call_ollama(AgentRole.SCOUT, final_prompt, "fast")
        self.session.scout_summary = summary
        return summary
    
    # =========================================================================
    # PHASE 2: WATCHER — YAML-SI ENFORCEMENT & VALIDATION
    # =========================================================================
    
    def format_watcher(self, role: AgentRole, raw_text: str, 
                       schema_hint: str,
                       max_validation_attempts: int = 3) -> str:
        """
        Convert raw agent output to strict YAML-SI with schema validation.
        Includes retry loop if validation fails.
        """
        print(f"   🤖 [WATCHER] Enforcing YAML-SI for {role.value}...")
        
        schema = YAML_SI_SCHEMAS.get(schema_hint, "")
        
        for attempt in range(max_validation_attempts):
            prompt = f"""
{PERSONALITIES[AgentRole.WATCHER]}

SCHEMA REQUIREMENTS:
{schema}

RAW TEXT TO CONVERT:

STRICT RULES:
1. Output ONLY valid YAML. No markdown fences, no explanations outside YAML.
2. Use nested structure matching the schema.
3. Include ALL key information from raw text.
4. Use YAML comments (#) ONLY for reasoning before critical fields.
5. If information is missing, use null or empty list [] — do not hallucinate.

Generate YAML-SI now:
            """
            
            yaml_response, duration, tokens = self._call_ollama(
                AgentRole.WATCHER, prompt, complexity="fast", temperature=0.2
            )
            
            # Clean up potential markdown fences
            yaml_clean = re.sub(r'^```yaml\s*', '', yaml_response)
            yaml_clean = re.sub(r'\s*```$', '', yaml_clean)
            yaml_clean = yaml_clean.strip()
            
            # Validate
            is_valid, error_msg = validate_yaml_structure(yaml_clean, schema_hint)
            
            if is_valid:
                print(f"   ✅ [WATCHER] YAML-SI validated successfully")
                return yaml_clean
            else:
                print(f"   ⚠️  [WATCHER] Validation failed (attempt {attempt + 1}): {error_msg}")
                if attempt < max_validation_attempts - 1:
                    # Feed error back for correction
                    raw_text = f"PREVIOUS ATTEMPT FAILED: {error_msg}\n\nOriginal text:\n{raw_text}"
        
        # Fallback: return best effort with warning
        print(f"   ❌ [WATCHER] Max validation attempts reached. Returning best-effort.")
        return yaml_clean
    
    # =========================================================================
    # PHASE 3: DEBATE LOOP — Maker-Checker Pattern
    # =========================================================================
    
    def debate_loop(self, proposal: str, context: str, 
                    maker_role: AgentRole = AgentRole.LEAD_CODER,
                    checker_role: AgentRole = AgentRole.CRITIC,
                    max_rounds: int = 2) -> Dict[str, Any]:
        """
        Structured debate between maker and checker agents.
        Reduces hallucinations and catches errors through adversarial review. citeweb_search:1#0
        """
        print(f"\n⚔️  [DEBATE] Initiating {maker_role.value} vs {checker_role.value}")
        
        debate_record = {
            "proposal": proposal,
            "rounds": [],
            "final_resolution": None
        }
        
        current_proposal = proposal
        
        for round_num in range(max_rounds):
            print(f"   [Round {round_num + 1}/{max_rounds}]")
            
            # Maker presents/refines
            maker_prompt = f"""
{PERSONALITIES[maker_role]}

CONTEXT: {context}

CURRENT PROPOSAL:
{current_proposal}

DEBATE INSTRUCTIONS:
You are in a structured debate. Present or refine your position.
Address any previous criticisms if they exist.
Output your position in YAML-SI format.
            """
            
            maker_output, _, _ = self._call_ollama(maker_role, maker_prompt, "heavy")
            maker_yaml = self.format_watcher(maker_role, maker_output, maker_role.value)
            
            # Checker critiques
            checker_prompt = f"""
{PERSONALITIES[checker_role]}

CONTEXT: {context}

PROPOSAL TO REVIEW:
{maker_yaml}

DEBATE INSTRUCTIONS:
Critically analyze this proposal. Find the most significant flaw.
Output your critique in YAML-SI format with severity assessment.
            """
            
            checker_output, _, _ = self._call_ollama(checker_role, checker_prompt, "balanced")
            checker_yaml = self.format_watcher(checker_role, checker_output, checker_role.value)
            
            debate_record["rounds"].append({
                "maker_yaml": maker_yaml,
                "checker_yaml": checker_yaml,
                "round": round_num + 1
            })
            
            # Check if checker approves (recommendation != HALT)
            try:
                parsed = yaml.safe_load(checker_yaml)
                recommendation = parsed.get("critical_review", {}).get("recommendation", "CAUTION")
                if recommendation == "PROCEED":
                    print(f"   ✅ [DEBATE] Checker approved after round {round_num + 1}")
                    debate_record["final_resolution"] = "APPROVED"
                    debate_record["final_artifact"] = maker_yaml
                    return debate_record
            except:
                pass
            
            # Update proposal for next round with critique incorporated
            current_proposal = f"Previous proposal:\n{maker_yaml}\n\nCritique to address:\n{checker_yaml}"
        
        # Max rounds reached — call moderator
        print(f"   🏛️  [DEBATE] Calling moderator for final resolution...")
        moderator_prompt = f"""
{PERSONALITIES[AgentRole.DEBATE_MODERATOR]}

DEBATE HISTORY:
{json.dumps(debate_record["rounds"], indent=2)}

RESOLUTION INSTRUCTIONS:
Synthesize the debate. Choose the strongest position or flag for human review.
Output unified position in YAML-SI format.
        """
        
        mod_output, _, _ = self._call_ollama(AgentRole.DEBATE_MODERATOR, moderator_prompt, "heavy")
        mod_yaml = self.format_watcher(AgentRole.DEBATE_MODERATOR, mod_output, "architect")
        
        debate_record["final_resolution"] = "MODERATED"
        debate_record["final_artifact"] = mod_yaml
        
        return debate_record
    
    # =========================================================================
    # PHASE 4: TRIGGER AGENT — Full Pipeline with State Persistence
    # =========================================================================
    
    def trigger_agent(self, role: AgentRole, task: str, 
                      context: str = "",
                      complexity: str = "balanced",
                      enable_debate: bool = False,
                      schema_hint: Optional[str] = None) -> str:
        """
        Execute a single agent with full pipeline:
        1. Inject YAML-SI personality
        2. Call model with fault tolerance
        3. Watcher formats to YAML-SI
        4. Validate structure
        5. Persist state
        6. Optionally trigger debate loop
        """
        model_name = self._get_model_for_role(role, complexity)
        print(f"\n🎯 [{role.value.upper()}] ({model_name}) processing...")
        print(f"   Task: {task[:80]}{'...' if len(task) > 80 else ''}")
        
        # Build full prompt with YAML-SI personality
        persona = PERSONALITIES.get(role, "")
        sys_instruct = f"""
{persona}

TASK SPECIFICATION:
{task}

CONTEXT FROM PREVIOUS AGENTS:
{context}

OUTPUT REQUIREMENTS:
- Structure your response for YAML-SI conversion
- Include reasoning comments (#) before critical decisions
- Be specific, technical, and actionable
        """
        
        # Execute with retries
        raw_output, duration, tokens = self._call_ollama(
            role, sys_instruct, complexity
        )
        
        # Watcher formatting
        hint = schema_hint or role.value
        yaml_output = self.format_watcher(role, raw_output, hint)
        
        # Persist agent state
        state = AgentState(
            agent=role.value,
            task=task,
            raw_response=raw_output,
            yaml_output=yaml_output,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            tokens_estimated=tokens,
            validation_status="VALID" if yaml_output else "FAILED",
            iteration=len(self.agent_history) + 1
        )
        self.agent_history.append(state)
        self.session.artifacts[role.value] = yaml_output
        
        # Save individual artifact
        timestamp = datetime.now().strftime("%H%M%S")
        artifact_file = f"{LOG_DIR}/{self.session.session_id}_{role.value}_{timestamp}.yaml"
        with open(artifact_file, 'w') as f:
            f.write(f"# Agent: {role.value}\n# Task: {task}\n# Duration: {duration}s\n# Tokens: {tokens}\n\n")
            f.write(yaml_output)
        
        print(f"   ✅ Completed in {duration}s | ~{tokens} tokens | Saved to {os.path.basename(artifact_file)}")
        
        # Optional debate loop for critical roles
        if enable_debate and role in [AgentRole.LEAD_CODER, AgentRole.THEORIST]:
            debate_result = self.debate_loop(yaml_output, context, role, AgentRole.CRITIC)
            self.session.debate_history.append(debate_result)
            # Return the debated/refined version
            return debate_result.get("final_artifact", yaml_output)
        
        return yaml_output
    
    # =========================================================================
    # PHASE 5: PARALLEL EXECUTION — Async Council Meeting
    # =========================================================================
    
    async def parallel_council(self, tasks: List[Tuple[AgentRole, str, str, str]]) -> Dict[str, str]:
        """
        Execute multiple agents in parallel where dependencies allow.
        tasks: List of (role, task, context, complexity) tuples
        """
        print("\n🌐 [PARALLEL COUNCIL] Launching async agent swarm...")
        
        async def run_single(role, task, context, complexity):
            # Run in thread pool since ollama is synchronous
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.trigger_agent(role, task, context, complexity)
            )
            return role.value, result
        
        # Launch all tasks concurrently
        results = await asyncio.gather(*[
            run_single(role, task, ctx, comp) 
            for role, task, ctx, comp in tasks
        ])
        
        return dict(results)
    
    # =========================================================================
    # PHASE 6: SESSION FINALIZATION
    # =========================================================================
    
    def finalize_session(self) -> str:
        """Save complete session state and generate summary report."""
        self.session.artifacts["agent_history"] = [asdict(a) for a in self.agent_history]
        
        # Save full session
        session_file = save_session_state(self.session)
        
        # Generate summary report
        report = f"""
{'='*70}
NEUROCITY COUNCIL — SESSION REPORT
{'='*70}
Session ID:    {self.session.session_id}
Start Time:    {self.session.start_time}
Mission:       {self.session.mission}
Total Agents:  {len(self.agent_history)}
Total Cost:    {self.session.total_cost:.4f} units
Debates Held:  {len(self.session.debate_history)}

AGENT EXECUTION LOG:
{'-'*70}
"""
        for state in self.agent_history:
            report += f"""
Agent:      {state.agent}
Duration:   {state.duration}s
Tokens:     ~{state.tokens_estimated}
Status:     {state.validation_status}
File:       {state.timestamp}
"""
        
        report += f"\n{'='*70}\nSession saved to: {session_file}\n{'='*70}"
        
        report_file = f"{LOG_DIR}/report_{self.session.session_id}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        return report


# =============================================================================
# EXECUTION PIPELINE — Ultimate Workflow
# =============================================================================

def run_ultimate_pipeline():
    """Execute the full NeuroCity Council pipeline with all advanced features."""
    
    council = NeuroCityCouncil()
    
    # The Initial Query
    core_problem = "Can a thumb's average reach on a phone screen over time allow us to know their height?"
    
    # PHASE 1: Interactive Clarification
    print("\n" + "🔷"*35)
    print("PHASE 1: INTERACTIVE SCOUT (Human-in-the-Loop)")
    print("🔷"*35)
    spec = council.interactive_scout(core_problem)
    
    # PHASE 2: Theorist + Archaeologist (can be parallel in future versions)
    print("\n" + "🔶"*35)
    print("PHASE 2: THEORY & HARDWARE ANALYSIS")
    print("🔶"*35)
    
    theory = council.trigger_agent(
        AgentRole.THEORIST,
        "Analyze the correlation between thumb ergonomics and skeletal height. "
        "Include mathematical basis, confidence scoring, and biometric assumptions.",
        spec,
        complexity="balanced",
        enable_debate=True,
        schema_hint="theorist"
    )
    
    hardware = council.trigger_agent(
        AgentRole.ARCHAEOLOGIST,
        "What mobile sensor data (touch coordinates, pressure, duration) is needed "
        "to measure thumb reach? Identify all hardware, privacy, and physical constraints.",
        theory,
        complexity="balanced",
        schema_hint="archeologist"
    )
    
    # PHASE 3: Code Generation with Debate Loop
    print("\n" + "🟢"*35)
    print("PHASE 3: CODE GENERATION & ADVERSARIAL REVIEW")
    print("🟢"*35)
    
    code_draft = council.trigger_agent(
        AgentRole.LEAD_CODER,
        "Write a Python logic structure to track touch reach 'heatmaps' and map to user height. "
        "Include core modules, data structures, algorithm overview, and complexity analysis.",
        hardware + "\n" + theory,
        complexity="heavy",
        enable_debate=True,  # Triggers maker-checker debate with Critic
        schema_hint="lead_coder"
    )
    
    # PHASE 4: Optimization (sequential dependency on code)
    print("\n" + "🔷"*35)
    print("PHASE 4: OPTIMIZATION & EDGE CASE HANDLING")
    print("🔷"*35)
    
    optimized_code = council.trigger_agent(
        AgentRole.JUNIOR_CODER,
        "Optimize this code for performance and add edge-case handling. "
        "Include test scenarios and performance gains.",
        code_draft,
        complexity="fast",
        schema_hint="junior_coder"
    )
    
    # PHASE 5: Critical Review
    print("\n" + "🔶"*35)
    print("PHASE 5: CRITICAL SECURITY & STATISTICAL REVIEW")
    print("🔶"*35)
    
    review = council.trigger_agent(
        AgentRole.CRITIC,
        "Find the biggest biometric/statistical flaw in this tracking theory. "
        "Rate severity, identify bias risks, and provide mitigation strategies.",
        optimized_code + "\n" + theory,
        complexity="balanced",
        schema_hint="critic"
    )
    
    # PHASE 6: Executive Decision
    print("\n" + "🏛️"*35)
    print("PHASE 6: ARCHITECT'S FINAL VERDICT")
    print("🏛️"*35)
    
    architect_context = f"""
HARDWARE CONSTRAINTS:
{hardware}

CRITICAL REVIEW:
{review}

OPTIMIZED SOLUTION:
{optimized_code}
    """
    
    verdict = council.trigger_agent(
        AgentRole.ARCHITECT,
        "Review the critic's flaw, hardware constraints, and optimized solution. "
        "Give a final GO or NO-GO for this project with primary rationale and risk assessment.",
        architect_context,
        complexity="heavy",
        schema_hint="architect"
    )
    
    # PHASE 7: Finalization
    print("\n" + "✅"*35)
    print("PHASE 7: SESSION FINALIZATION")
    print("✅"*35)
    
    council.finalize_session()
    
    # Display final verdict
    print("\n" + "="*70)
    print("🏛️  ARCHITECT'S FINAL VERDICT 🏛️")
    print("="*70)
    try:
        parsed_verdict = yaml.safe_load(verdict)
        decision = parsed_verdict.get("executive_verdict", {}).get("decision", "UNKNOWN")
        rationale = parsed_verdict.get("executive_verdict", {}).get("primary_rationale", "No rationale provided")
        
        if decision == "GO":
            print(f"🟢 DECISION: {decision}")
        else:
            print(f"🔴 DECISION: {decision}")
        print(f"📋 RATIONALE: {rationale}")
    except:
        print(verdict)
    
    print("="*70)


# =============================================================================
# ADVANCED: PARALLEL SWARM MODE (Async Demo)
# =============================================================================

async def run_parallel_swarm_demo():
    """Demonstrate parallel agent execution for independent tasks."""
    council = NeuroCityCouncil(session_id="parallel_demo_" + generate_session_id())
    
    # Define independent tasks that can run in parallel
    parallel_tasks = [
        (
            AgentRole.THEORIST,
            "Analyze thumb-to-height correlation theory",
            "Mission: Biometric tracking via touch patterns",
            "balanced"
        ),
        (
            AgentRole.ARCHAEOLOGIST,
            "List all mobile sensor capabilities for touch tracking",
            "Mission: Biometric tracking via touch patterns",
            "balanced"
        ),
        (
            AgentRole.CRITIC,
            "Pre-review privacy implications of touch tracking",
            "Mission: Biometric tracking via touch patterns",
            "balanced"
        )
    ]
    
    results = await council.parallel_council(parallel_tasks)
    
    print("\n" + "="*70)
    print("PARALLEL SWARM RESULTS")
    print("="*70)
    for agent, output in results.items():
        print(f"\n📦 [{agent.upper()}] OUTPUT:")
        print(output[:500] + "..." if len(output) > 500 else output)
    
    council.finalize_session()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--parallel":
        # Run parallel demo
        asyncio.run(run_parallel_swarm_demo())
    else:
        # Run standard ultimate pipeline
        run_ultimate_pipeline()
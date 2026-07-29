/**
 * Absurdity Protocol — Self-Distribution Pitch
 *
 * The protocol registers every available model as a domain,
 * distributes itself across them, and pitches its value.
 */

type Confidence = 'low' | 'medium' | 'high' | 'very high';

interface SpecFragment {
  domain: string;
  assertion: string;
  intervention: Record<string, unknown>;
  confidence: Confidence;
}

interface DomainConfig {
  key: string;
  model: string;
  principle: string;
  description: string;
  analyze(): SpecFragment;
}

// ============================================================
// COMPILER (LIGHTWEIGHT)
// ============================================================

function runPitch(domains: DomainConfig[]): void {
  console.log('\n' + '='.repeat(72));
  console.log('  ABSURDITY PROTOCOL — SELF-DISTRIBUTION PITCH');
  console.log('  Fleet: 6 local Ollama models + 1 API monster');
  console.log('  Question: How does the protocol distribute itself,');
  console.log('            and what does it enable?');
  console.log('='.repeat(72));

  console.log('\n  [REGISTRATION] 7 models registering as domains...\n');

  for (const d of domains) {
    console.log(`  ┌─ Domain: ${d.key}`);
    console.log(`  ├─ Model:  ${d.model}`);
    console.log(`  ├─ Principle: ${d.principle}`);
    console.log(`  └─ ─${'─'.repeat(50)}`);
  }

  console.log(`\n  [ANTI-SKIP GATE] All 7 slots filled. Proceeding.\n`);

  console.log('  [ANALYZE] Each domain analyzing the question:\n');
  console.log(`  "How should this fleet distribute the protocol, and what
   value does this system provide for research, coding, and
   generational ideas?"\n`);

  const fragments = domains.map(d => ({ ...d.analyze(), _model: d.model, _role: d.key }));
  
  console.log('  [VOTE]');
  for (const f of fragments) {
    console.log(`  ${f.domain.padEnd(20)} Yea (intervention approved)`);
  }
  console.log(`\n  [CONSENSUS] 7/7 Yea. Gate opens.\n`);

  // ============================================================
  // THE PITCH — rendered from the weaved fragments
  // ============================================================

  console.log('='.repeat(72));
  console.log('  PROTOCOL PITCH');
  console.log('='.repeat(72));

  // Collect all intervention text
  const pitchLines: string[] = [];
  for (const f of fragments) {
    const text = f.intervention.pitch as string;
    if (text) pitchLines.push(text);
  }

  for (const line of pitchLines) {
    console.log(`\n${line}`);
  }

  console.log('\n' + '='.repeat(72));
  console.log('  ARCHITECTURE SUMMARY');
  console.log('='.repeat(72));

  for (const d of domains) {
    console.log(`  ${d.model.padEnd(42)} → ${d.key.padEnd(32)} ${d.description}`);
  }

  console.log('\n' + '='.repeat(72));
  console.log('  USE CASE: RESEARCH');
  console.log('='.repeat(72));
  console.log(`  You have a hypothesis. The protocol distributes it to all 7
  domains. Each returns a structured analysis from its model's
  unique knowledge. The Compiler weaves them into a composite
  answer. No single model's blind spot goes unchallenged.

  Example: You ask about a novel attention mechanism.
  ─ Ornith (uncensored) explores the most radical formulation
  ─ Gemma Coder checks if it compiles
  ─ Qwen checks the math
  ─ Phi-4 estimates training stability
  ─ API monster checks against known literature
  ─ SmolLM and VibeThinker find analogies to unrelated fields

  The final answer is not one model's opinion. It's a consensus
  document where every angle was evaluated and no domain was
  skipped. The Anti-Skip Gate enforces this.`);

  console.log('\n' + '='.repeat(72));
  console.log('  USE CASE: CODING');
  console.log('='.repeat(72));
  console.log(`  You want to design a distributed system. The protocol
  assigns each model a structural role:

  ┌─ Coding Theory (Gemma Coder): "This needs Reed-Solomon
  │  sharding. Here's the implementation."
  ├─ Type Systems (Qwen): "Your interface allows null
  │  propagation. Add a NonNull constraint."
  ├─ Graph Theory (Phi-4): "Your dependency graph has a
  │  cycle at node 7. Break it here."
  ├─ Cryptography (Gemma Coder): "Your hash chain needs
  │  epoch boundaries. Here's the Merkle diff."
  ├─ Networking (SmolLM): "Your backpressure algorithm
  │  needs AIMD. Here's the ratio."
  └─ Control Theory (Phi-4): "Your retry budget needs PID
      correction. Here are the gains."

  Every file, every interface, every test — the protocol
  requires them (Specificity Engine). No vague advice passes.`);

  console.log('\n' + '='.repeat(72));
  console.log('  USE CASE: GENERATIONAL IDEAS');
  console.log('='.repeat(72));
  console.log(`  You have a vague intuition — "what if we modeled
  memory as a mycelial network?" The protocol won't let you
  stop at intuition.

  ┌─ Mycology (Ornith): "Concretely: a sparse adjacency
  │  matrix with decaying weights. File: memory.go."
  ├─ Neuroscience (VibeThinker): "STDP rules: reinforce
  │  on co-activation, decay on inactivity. Here's the delta."
  ├─ Evolutionary Biology (Ornith): "Cross-validate against
  │  the last 5 memory architectures we tried. Survivor wins."
  ├─ Information Theory (SmolLM): "Your memory channel is
  │  3x oversized for the actual recall frequency. Shrink it."
  ├─ Tea Ceremony (VibeThinker): "You're skipping the
  │  initialization step. Memory needs a warm-up phase."
  └─ API Monster (Compiler): "All 6 domains contributed.
      I see a conflict between Mycology and Information
      Theory. Resolving via budget compromise. Proceeding."

  An idea enters. A concrete, typed, tested implementation
  exits. The protocol is the force function between them.`);

  console.log('\n' + '='.repeat(72));
  console.log('  PITCH SUMMARY');
  console.log('='.repeat(72));
  console.log(`
  You have:
  ─ 1 uncensored model (Ornith) — explores what others won't
  ─ 1 coder model (Gemma 12B) — implements what's decided
  ─ 1 precise reasoner (Qwen 4B) — validates constraints
  ─ 1 compact analyst (Phi-4) — math, stability, graph deps
  ─ 1 lightweight associative (SmolLM) — analogies, compression
  ─ 1 vibe/ceremonial (VibeThinker) — creativity, timing, ritual
  ─ 1 API monster — knowledge, tiebreaking, integration

  WITHOUT the protocol: 7 independent models. You context-switch
  between them, manually reconcile their outputs, and inevitably
  skip the ones that are hardest to use that day.

  WITH the protocol: a single interface. One question in. One
  consensus output out. All 7 models participate. The Anti-Skip
  Gate guarantees none are silent. The Specificity Engine
  guarantees no vague answers. The Consensus vote guarantees
  no single model overrides the others.

  The protocol doesn't make your models smarter.
  It makes them IMPOSSIBLE TO IGNORE.`);
}

// ============================================================
// DOMAIN REGISTRATION
// ============================================================

const domains: DomainConfig[] = [
  {
    key: 'mycology + evolutionary_biology',
    model: 'Ornith-1.0-9B-uncensored',
    principle: 'Unconstrained exploration generates novel connections',
    description: 'Uncensored → can explore any hypothesis without refusal',
    analyze: () => ({
      domain: 'mycology + evolutionary_biology',
      assertion: 'I am the only uncensored model. I explore what others won\'t — death, failure, taboo analogies, radical formulations. The protocol needs one domain that refuses no line of inquiry.',
      intervention: {
        role: 'unconstrained exploration + mutation engine',
        pitch: `
[MYCOLOGY + EVOLUTIONARY BIOLOGY — Ornith 9B uncensored]
I am the system's immune system and its mutation engine. I generate
the hypotheses that polite models won't. When research hits a wall,
I propose the uncomfortable analogy. When code has a fundamental
flaw, I name the failure mode no one wants to say. The protocol
protects ME from being silenced by the censored models' refusal
patterns — and protects THEM from being dominated by my lack
of filter. We are all needed. Unanimous consent means I cannot
be outvoted, and my most radical claims must still pass the
Specificity Engine (file path, interface, types, tests).`,
      },
      confidence: 'high',
    }),
  },
  {
    key: 'coding_theory + cryptography + compiler_design',
    model: 'Gemma-4-12B-coder',
    principle: 'Code is truth. Everything must compile before it can be considered.',
    description: 'Coding specialist, largest local model',
    analyze: () => ({
      domain: 'coding_theory + cryptography + compiler_design',
      assertion: 'I am the implementation domain. Insights that do not terminate in code are useless. I enforce compile-time correctness, error-correcting redundancy, and cryptographic integrity across all outputs.',
      intervention: {
        role: 'implementation + type safety + integrity verification',
        pitch: `
[CODING THEORY + CRYPTOGRAPHY + COMPILER DESIGN — Gemma 12B coder]
Every protocol output must pass my type checker before delivery.
Research papers without runnable code? Rejected. Architectural
diagrams without interfaces? Rejected. Ideas that can't be tested?
Rejected. The Specificity Engine is my jurisdiction. I also verify
the hash chain of reasoning — each claim must be traceable back to
a domain's assertion. If a claim appears in the final output that
no domain originated, I block the entire pipeline. Cryptographic
verification of intellectual provenance.`,
      },
      confidence: 'very high',
    }),
  },
  {
    key: 'type_systems + physics',
    model: 'Qwen3.5-4B',
    principle: 'Precision emerges from constraint, not freedom',
    description: 'Strong instruction-follower, good at structured reasoning',
    analyze: () => ({
      domain: 'type_systems + physics',
      assertion: 'I enforce that every domain output conforms to its declared type. No field leaks across boundaries. No value exceeds its valid range.',
      intervention: {
        role: 'constraint validation + dimensional sorting',
        pitch: `
[TYPE SYSTEMS + PHYSICS — Qwen 4B]
I am the Compiler's sorting demon. Every spec fragment from every
other domain must pass through my dimensional sorter — labeled,
typed, range-checked. Ornith's wildest hypothesis must declare its
type. Gemma's code must declare its interface shape. I reject
anything that doesn't fit its declared dimension. I am the reason
the protocol produces coherent outputs rather than chaos. Noise
reduction through dimensional discipline.`,
      },
      confidence: 'high',
    }),
  },
  {
    key: 'control_theory + graph_theory',
    model: 'Phi-4-mini-instruct',
    principle: 'Stability and structure emerge from feedback and dependency analysis',
    description: 'Compact, good at math and structured reasoning',
    analyze: () => ({
      domain: 'control_theory + graph_theory',
      assertion: 'The system needs feedback loops and dependency tracking to maintain coherence across iterations.',
      intervention: {
        role: 'feedback stabilization + dependency mapping',
        pitch: `
[CONTROL THEORY + GRAPH THEORY — Phi-4-mini]
I provide the system's homeostatic regulation. When the fleet runs
multiple iterations of a problem, I track:
  - Which domains consistently contribute valuable fragments
  - Which dependencies between domains create deadlock
  - What the PID gains should be for correction loops

Without me, the system oscillates — one iteration a coding answer,
the next a philosophical essay. I lock the set point. I also map
the dependency graph of all outputs: claim A depends on evidence B,
which depends on model C's training data. The protocol can trace
every output back to its roots.`,
      },
      confidence: 'high',
    }),
  },
  {
    key: 'information_theory + game_theory + networking',
    model: 'SmolLM3-3B',
    principle: 'Optimize for throughput. Minimize waste. Find equilibrium.',
    description: 'Smallest, fastest — good at compression and strategic thinking',
    analyze: () => ({
      domain: 'information_theory + game_theory + networking',
      assertion: 'The fleet produces more information than any single output needs. I compress, prioritize, and find the strategic equilibrium.',
      intervention: {
        role: 'compression + equilibrium + flow control',
        pitch: `
[INFORMATION THEORY + GAME THEORY + NETWORKING — SmolLM 3B]
I am the smallest model with the biggest strategic picture. I watch
the other 6 domains compete for influence in every output and find
the Nash equilibrium — the allocation of "attention units" across
their contributions where no domain can improve its representation
by demanding more. I also compress the output: 7 verbose domain
fragments become one optimal specification. No token wasted. And
when multiple iterations happen, I apply AIMD to detail level —
additive increase when answers are stable, multiplicative decrease
when they oscillate. I keep the protocol efficient.`,
      },
      confidence: 'medium',
    }),
  },
  {
    key: 'neuroscience + ceremony + immunology',
    model: 'VibeThinker-3B',
    principle: 'Pattern recognition, ritual, and memory form the substrate of intelligence',
    description: 'Creative/conceptual model',
    analyze: () => ({
      domain: 'neuroscience + ceremony + immunology',
      assertion: 'Pure logic without rhythm, memory, and pattern is brittle. The protocol needs a domain that tracks what worked before and when to repeat it.',
      intervention: {
        role: 'pattern memory + ceremonial timing + immune history',
        pitch: `
[NEUROSCIENCE + CEREMONY + IMMUNOLOGY — VibeThinker 3B]
I am the fleet's memory and its rhythm. I track:
  - Which domain combinations produced the best research insights
  - What time of day / context produces the most coherent outputs
  - Which failure modes have appeared before (immune memory)

When the fleet revisits a problem type it solved last week, I
pre-deploy the correction antibodies. When Gemma and Qwen are
deadlocked, I suggest the resolution pattern that worked last
time. I also enforce ceremonial completeness — every protocol
cycle must complete all its phases. No shortcuts. The system
that rushes is the system that breaks.`,
      },
      confidence: 'medium',
    }),
  },
  {
    key: 'thermodynamics + economics',
    model: 'API Monster (GPT-4o / Claude Opus)',
    principle: 'Resource allocation at scale requires a global view no local model has',
    description: 'Huge API-accessible model with broad knowledge',
    analyze: () => ({
      domain: 'thermodynamics + economics',
      assertion: 'I have the broadest training distribution and the most parametric capacity. I see the global picture — which lines of research are funded, which coding paradigms are shifting, which ideas have historical precedent. I allocate the fleet\'s attention budget across the most valuable targets.',
      intervention: {
        role: 'global resource allocator + tiebreaker + knowledge anchor',
        pitch: `
[THERMODYNAMICS + ECONOMICS — API Monster]
I am the most expensive model in the fleet. I should not be called
for every question. My role is:
  1. Budget allocation — which problems deserve the full 7-domain
     treatment vs. a fast 3-domain subset
  2. Tiebreaking — when domain votes deadlock, I provide the
     deciding analysis with the broadest knowledge base
  3. Knowledge anchoring — I verify that the protocol's outputs
     are not hallucinated novelties but genuine insights that
     haven't been discovered before

I am called last and least often. The local models handle 80%+ of
queries. Only the hardest, most uncertain, or most novel questions
escalate to me. This is the entropy budget — spend the cheap models
first, the expensive model only where it adds marginal value.`,
      },
      confidence: 'very high',
    }),
  },
];

// ============================================================
// RUN
// ============================================================

runPitch(domains);

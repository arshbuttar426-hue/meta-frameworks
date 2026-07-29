# Absurdity Coding — Methodology Overlay

> Drop this file into any project as CLAUDE.md, .cursorrules, or AGENTS.md to activate the Absurdity Coding methodology on top of your existing agent harness.

## Core Metric: Information Retention Ratio (IRR)

```
IRR = preserved_fields / total_input_fields
```

Every pipeline stage that converts structured data to text MUST have IRR measured. IRR < 0.3 = FAIL, IRR < 0.5 = WARN.
- **Template filling at T=0.3 instead of T=1.5 recovers ~55% of lost data** — this is the single highest-impact change you can make.

## Pre-Code Veto (Specificity Engine)

Before writing ANY code, ALL 5 must pass:

| Criteria | Check |
|---|---|
| Exact file path named | YES/NO |
| Function/class named | YES/NO |
| Inputs/outputs typed | YES/NO |
| ≥3 test cases planned | YES/NO |
| Call site identified | YES/NO |

Any NO → reject proposal. Don't proceed until all pass.

## Temperature Control

| Stage | Temp | Why |
|---|---|---|
| Template filling, transforms | 0.1–0.3 | No creativity needed |
| Code generation with specs | 0.3–0.5 | Follow structure |
| Creative / novel solutions | 0.7–1.2 | Exploration |
| Brainstorming | 1.2–1.5 | Maximum variation |

## 11 Domain Patterns (Quick Reference)

| Domain | Pattern | When |
|---|---|---|
| 0 **Nature** | ALL constraints apply simultaneously. No dropping. | Every artifact, always |
| 1 Biology | Distributed specialist modules via typed ports | God class doing too much |
| 2 Physics (Maxwell) | Sort into labeled sections, don't summarize | Template filling, prompt assembly |
| 3 Chemistry | Static read-only templates, data flows through | Code gen, config gen, scaffolding |
| 4 Biomechanics | Composition over inheritance, max depth 2 | Class hierarchies >2 levels |
| 5 Philosophy | Decisions go to the component with most context | Pipelines, orchestration |
| 6 Psychology | Explicit persistence clauses for off-screen state | Sessions, long-running workflows |
| 7 Medicine (Homeostat) | Define set points, measure, correct if drifted | State sync, drift detection |
| 8 Economics (VCG) | Truthful auction when multiple resources compete | Multi-model routing, algorithm selection |
| 9 Cryptography | Hash chain integrity verification | ETL, state machines, audit trails |
| **10 Morphogenesis** | **Connected growth + local decision + proportional friction** | **Generative code, emergent structure** |
| -1 Parsimony | Simplest solution wins. Evidence required. | Always — the default veto |

### Domain 10: Morphogenesis — Connected Constraint Propagation

**Principle**: Form grows from connected steps, each determined by local constraints at that point in the sequence. No pre-planned paths. Each step connects to the previous state. The final structure is the fossil record of every constraint negotiation.

**Pattern**: Instead of specifying a target shape and working backward, specify a starting point and the rules for each step. The shape emerges from the constraint iteration.

**When to use**: Any system where output structure should emerge from iterative rules rather than be pre-specified. Generative rendering, recursive structures, data transformation pipelines, evolutionary architecture.

**Implementation patterns**:

```
1. Start from ONE point (entry function, root component)
2. Each step connects to the previous endpoint
3. Direction determined by CURRENT state, not target
4. Friction proportional to size — complexity naturally limits growth
5. When friction exceeds threshold → branch (new module/function)
6. Territory claimed per module — don't cross without permission
7. Structure IS the growth sequence — never edit the fossil record
```

**Implementation reference**:
```python
class Growth:
    """A connected sequence. Each step from the previous state.
    Friction scales with age — bigger = harder to extend."""
    def __init__(self, x, y, base_lw, color, max_age, friction=0.05):
        self.hx, self.hy = x, y  # current position (previous endpoint)
        self.base_lw = base_lw
        self.color = color
        self.max_age = max_age
        self.friction = friction  # proportional drag
        self.age = 0
        self.history = [(x, y)]

    @property
    def t(self):
        return self.age / max(self.max_age, 1)

    @property
    def alive(self):
        return self.age < self.max_age

    def step_scale(self):
        """Friction: bigger → shorter steps. Never reaches 0."""
        return 1.0 / (1.0 + self.friction * self.age)

    def step_to(self, x, y):
        if self.age >= self.max_age:
            return False
        self.history.append((x, y))
        self.hx, self.hy = x, y
        self.age += 1
        return True
```

**Tests**: 1. Same seed → identical growth every time. 2. Higher friction → shorter total length. 3. Growth naturally stops when friction exceeds step size.

**Falsification**: A system using morphogenetic constraints produces LESS coherent output than one using traditional top-down planning for the same problem.

## Key Equations

```
IRR = |structured_output| / |structured_input|
    = 1.0 (lossless) → 0.34 (lossy, T=1.5) → 0.89 (catalytic + T=0.3)

estimated_tokens = depth * 50 * complexity_factor

bid_i = (1/speed_i) * (1 + (1-task_score_i)²) / reliability_i
winner = argmin(bid), price = second_lowest
```

## Verification Gates

1. **Specificity Engine** (re-run) — any NO → reject
2. **Cyclomatic complexity < 3**, Module size < 50 lines, Coverage > 80%
3. **Intent alignment**: > 0.85 publish, > 0.70 review, else escalate
4. **No silent degradation** — explicit error or documented fallback

---

*Every insight terminates in code. Every path is predetermined before execution. No abstraction without a file path.*

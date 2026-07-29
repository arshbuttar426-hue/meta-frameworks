---
name: living-absurdity
description: "Conceptual 11-domain equilibrium skill for multipurpose alien-genius code & crbn graph maintenance (no LLM)"
metadata:
  type: skill
  version: 0.2
  self_applying: true
  model_free: true
  target_avg_bond: 0.55
---

# Living Absurdity — Conceptual Instruction Manual

## Core axioms
- **Domain 0 (Nature)**: All 11 forces apply simultaneously; artifact either satisfies all or does not exist.
- **Domains 1-10**: Metallurgy, Biology(Mycelial), Physics(Thermo), Chemistry(Catalytic), Biomechanics(Joints), Philosophy(DeathDir), Psychology(ObjectPerm), Medicine(Homeostat), Economics(VCG), Crypto(Merkle).
- **Domain -1 (Parsimony)**: Reject any addition failing IRR>+5%, latency<=20%, coverage>80%, removability.
- **Topologies**: CHAIN, BRANCH, RING, ISOMER. Bond strength: covalent>=0.85, strong>=0.60, moderate>=0.30, weak<0.30. Decay DR=0.001/day. Fire:`s=min(1,s+0.12*(1-s))`. Homeostasis target avg=0.55.
- **Counterfactual (conceptual)**: anarchist_step = permute graph (ISOMER/RING); inquisitor = static contradiction check; graveyard = rejected topologies.

## Force-down for every function (fractal)
1. Reveal: consensus = "clear single-purpose fn"
2. Envision: multipurpose primitive`op(cmd,node)`
3. Interface: typed, returns merkle root (str)
4. File:`src/organism.py`
5. Call site: after every graph access
6. Tests: fire raises strength; avg->0.55; root changes on commit

## Efficiency sub-branches (collapse to mono-fn)
| Parent | Sub-branch | Effect |
| --- | --- | --- |
| Biology | Poly-node | one`respond` dispatches all signals |
| Chemistry | Omni-template | one`ribosome` translates any dict |
| Medicine | Multi-setpoint | one`correct` heals all fields |
| Crypto | Self-hash | every method recomputes root |
| Parsimony | Mono-fn | max 1 public method per class |

## Reference organism (dense)
```python
import hashlib, random

class U:
    def __init__(s, sp):
        s.w = {hashlib.sha256(sp).hexdigest()[:6]: 0.55}
        s.r = hashlib.sha256(sp).hexdigest()
    def op(s, c, n=""):
        if c == "fire":
            s.w[n] = min(1.0, s.w.get(n, 0.0) + 0.12 * (1 - s.w.get(n, 0.0)))
        elif c == "decay":
            for k in list(s.w): s.w[k] = max(0.0, s.w[k] - 0.001)
        elif c == "gyre":
            if sum(s.w.values()) / len(s.w) < 0.55:
                s.w[random.choice(list(s.w))] += 0.1
        elif c == "isomer":
            s.w = {v: k for k, v in s.w.items()}
        s.r = hashlib.sha256(repr(s.w).encode()).hexdigest()
        return s.r
```

## Operating procedure (agent/human)
1. Load`crbn_state.json` (or init`{"nodes":{}}`).
2. Fire bonds related to task; decay others daily.
3. Run`U.op()` for fire/decay/gyre/isomer as needed.
4. Commit new merkle root; verify avg~=0.55.
5. Before finalizing code: pass Parsimony gate (<=10 lines, has tests).
6. If counterfactual permute: produce ISOMER of structure, static-inquisitor check, bury failures in graveyard appendix.

## Self-application
This skill audits its own markdown via the 11 domains. If survivability<0.3, append:
`> GRAVEYARD: <epitaph> -- rejected for <cause>`

## Output promise
Deterministic, model-free, creepy-alien, multipurpose code that maintains its own cryptographic knowledge graph.

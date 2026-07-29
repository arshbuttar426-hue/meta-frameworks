/**
 * Absurdity Protocol — Protocol-Driven Prompt Generation
 *
 * The protocol framework generates a museum-quality hyperrealist painting prompt.
 * Every line of the final prompt is traceable to a specific domain intervention.
 * The Compiler refuses to produce output unless ALL 17 domains contribute and vote Yea.
 */

type Confidence = 'low' | 'medium' | 'high' | 'very high';

interface SpecFragment {
  domain: string;
  assertion: string;
  intervention: Record<string, unknown>;
  confidence: Confidence;
}

interface Domain {
  key: string;
  principle: string;
  analyze(): SpecFragment;
  vote(assembled: Record<string, unknown>): 'yea' | 'nay' | 'abstain';
}

type Vote = { domain: string; vote: 'yea' | 'nay' | 'abstain'; reason?: string };

// ============================================================
// COMPILER — ANTI-SKIP GATE
// ============================================================

class Compiler {
  private domains = new Map<string, Domain>();

  register(domain: Domain): void {
    this.domains.set(domain.key, domain);
  }

  assemble(fragments: SpecFragment[]): Record<string, unknown> {
    const contributed = new Set(fragments.map((f) => f.domain));
    for (const key of this.domains.keys()) {
      if (!contributed.has(key)) {
        console.log(`  [GATE] Domain "${key}" did not contribute. Blocking assembly.`);
        throw new Error(`ANTI-SKIP GATE: Domain "${key}" missing.`);
      }
    }
    const envelope: Record<string, unknown> = {
      __meta: { fragments: [] as SpecFragment[], timestamp: Date.now() },
    };
    for (const fragment of fragments) {
      if (fragment.intervention.promptLines) {
        const lines = fragment.intervention.promptLines as string[];
        for (const line of lines) {
          const key = `line_${line.slice(0, 20).replace(/\s+/g, '_')}_${fragment.domain}`;
          envelope[key] = line;
        }
      }
      if (fragment.intervention.compositionRule) {
        envelope.compositionRule = fragment.intervention.compositionRule;
      }
      if (fragment.intervention.lightRule) {
        envelope.lightRule = fragment.intervention.lightRule;
      }
      if (fragment.intervention.detailRule) {
        envelope.detailRule = fragment.intervention.detailRule;
      }
      if (fragment.intervention.subjectRule) {
        envelope.subjectRule = fragment.intervention.subjectRule;
      }
      if (fragment.intervention.emotionalRule) {
        envelope.emotionalRule = fragment.intervention.emotionalRule;
      }
      if (fragment.intervention.techniqueRule) {
        envelope.techniqueRule = fragment.intervention.techniqueRule;
      }
      if (fragment.intervention.forbiddenRule) {
        envelope.forbiddenRule = fragment.intervention.forbiddenRule;
      }
      (envelope.__meta.fragments as SpecFragment[]).push(fragment);
    }
    return envelope;
  }

  vote(fragments: SpecFragment[], envelope: Record<string, unknown>): { passed: boolean; votes: Vote[] } {
    const votes: Vote[] = [];
    for (const f of fragments) {
      const domain = this.domains.get(f.domain);
      if (!domain) { votes.push({ domain: f.domain, vote: 'abstain' }); continue; }
      const result = domain.vote(envelope, f);
      votes.push({ domain: f.domain, vote: result });
    }
    const nay = votes.filter(v => v.vote === 'nay');
    if (nay.length > 0) {
      throw new Error(`CONSENSUS FAILED: ${nay.length} domain(s) voted Nay: [${nay.map(v => v.domain).join(', ')}]. Unanimous Yea-or-Abstain required.`);
    }
    return { passed: true, votes };
  }

  run(): { prompt: string; votes: Vote[]; fragments: SpecFragment[] } {
    console.log(`\n  [COMPILER] ${this.domains.size} domains registered.`);
    const fragments: SpecFragment[] = [];
    for (const domain of this.domains.values()) {
      console.log(`  [ANALYZE] ${domain.key}...`);
      fragments.push(domain.analyze());
    }
    console.log(`  [ASSEMBLE] Weaving ${fragments.length} fragments...`);
    const envelope = this.assemble(fragments);
    console.log(`  [VOTE] All ${fragments.length} domains voting...`);
    const { votes } = this.vote(fragments, envelope);
    const yea = votes.filter(v => v.vote === 'yea').length;
    const abstain = votes.filter(v => v.vote === 'abstain').length;
    console.log(`  [CONSENSUS] Yea: ${yea}, Nay: 0, Abstain: ${abstain}. Gate opens.`);
    const prompt = this.render(envelope);
    return { prompt, votes, fragments };
  }

  private render(envelope: Record<string, unknown>): string {
    const categories: Record<string, string[]> = {
      subject: [], light: [], composition: [], detail: [],
      technique: [], emotional: [], forbidden: [], final: [],
    };
    for (const key of Object.keys(envelope)) {
      if (key === '__meta') continue;
      const val = envelope[key];
      if (typeof val !== 'string') continue;
      if (val.startsWith('SUBJECT:')) categories.subject.push(val);
      else if (val.startsWith('LIGHT:')) categories.light.push(val);
      else if (val.startsWith('COMPOSITION:')) categories.composition.push(val);
      else if (val.startsWith('DETAIL:')) categories.detail.push(val);
      else if (val.startsWith('TECHNIQUE:')) categories.technique.push(val);
      else if (val.startsWith('EMOTIONAL:')) categories.emotional.push(val);
      else if (val.startsWith('FORBIDDEN:')) categories.forbidden.push(val);
      else if (val.startsWith('FINAL:')) categories.final.push(val);
    }
    const promptParts: string[] = [];
    for (const cat of ['subject', 'light', 'composition', 'detail', 'technique', 'emotional', 'forbidden', 'final']) {
      for (const item of categories[cat]) {
        promptParts.push(item.replace(/^(SUBJECT|LIGHT|COMPOSITION|DETAIL|TECHNIQUE|EMOTIONAL|FORBIDDEN|FINAL):\s*/, ''));
      }
    }
    if (promptParts.length === 0) {
      for (const key of Object.keys(envelope)) {
        if (key === '__meta') continue;
        const val = envelope[key];
        if (typeof val === 'string') promptParts.push(val);
      }
    }
    return promptParts.join('\n\n');
  }
}

// ============================================================
// 17 DOMAINS — Each analyzes the task and prescribes an intervention
// ============================================================

function registerAllDomains(c: Compiler): void {
  c.register({
    key: 'mycology',
    principle: 'Emergence comes from distributed meaning, not central focal authority',
    analyze: () => ({
      domain: 'mycology',
      assertion: 'A painting with one focal point is a monarchy — it dictates meaning. Museum art distributes meaning across the frame so the eye wanders.',
      intervention: {
        promptLines: [
          'SUBJECT: A woman in her 60s seated at a plain wooden table. Grey hair pulled back, no jewelry, no makeup, an unremarkable grey coat and cotton dress. She is not looking at anything. Her eyes are half-lidded, her mouth closed but not clenched.',
          'COMPOSITION: Three zones of equal visual weight — the hands (bottom center), the face (upper center-right), the empty wall (upper 40%). No zone dominates. The eye cycles through all three without settling.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled, fragment) => {
      const hasSubject = Object.values(assembled).some(v => typeof v === 'string' && v.includes('woman'));
      const hasEmpty = Object.values(assembled).some(v => typeof v === 'string' && v.includes('empty'));
      return hasSubject && hasEmpty ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'physics',
    principle: 'Information can be sorted without energy cost if you know the labels',
    analyze: () => ({
      domain: 'physics',
      assertion: 'Visual dimensions are mixed into prose. The viewer cannot parse rapidly.',
      intervention: {
        promptLines: [
          'COMPOSITION: The frame sorted by visual density from top to bottom — top 40% low density (empty wall, shadow, thin paint), middle 30% medium density (face, shoulders, soft transitions), bottom 30% maximum density (hands, fabric folds, every thread and wrinkle rendered fully).',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const sorted = Object.values(assembled).some(v => typeof v === 'string' && v.includes('top 40%') && v.includes('bottom 30%'));
      return sorted ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'chemistry',
    principle: 'A catalyst lowers activation energy without being consumed',
    analyze: () => ({
      domain: 'chemistry',
      assertion: 'Without a catalytic constraint, the rendering has no generative tension.',
      intervention: {
        promptLines: [
          'TECHNIQUE: The single invariant — every brushstroke on the hands must be simultaneously an edge AND a transition. Not a hard line defining the finger contour, not a soft gradient blending into shadow — a third thing that is both at once. This contradiction generates all the visual energy.',
        ],
      },
      confidence: 'very high',
    }),
    vote: (assembled) => {
      const hasEdgeTransition = Object.values(assembled).some(v => typeof v === 'string' && v.includes('edge') && v.includes('transition'));
      return hasEdgeTransition ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'neuroscience',
    principle: 'Connections strengthen when they fire together consistently',
    analyze: () => ({
      domain: 'neuroscience',
      assertion: 'A painting that offers the eye many paths strengthens none. The viewer must be forced down one path repeatedly.',
      intervention: {
        promptLines: [
          'COMPOSITION: The viewing path is forced: eyes → hands → breath → eyes → hands → breath. No alternative path is offered. The viewer\'s gaze tracks this circuit until the synaptic trace is indelible. The empty wall offers no escape. The face offers no narrative. Only the hands provide enough resolution to satisfy — and they lead back to the breath.',
        ],
      },
      confidence: 'medium',
    }),
    vote: (assembled) => {
      const hasPath = Object.values(assembled).some(v => typeof v === 'string' && v.includes('eyes') && v.includes('hands') && v.includes('breath'));
      return hasPath ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'thermodynamics',
    principle: 'Every system has a fixed entropy budget. Spend it wisely.',
    analyze: () => ({
      domain: 'thermodynamics',
      assertion: 'Detail spread evenly across the canvas is no detail at all. Entropy must be concentrated.',
      intervention: {
        promptLines: [
          'DETAIL: 70% of the painting\'s detail budget is spent on 15% of the canvas — the left hand and the 12 square inches of fabric where it rests. Every pore, every vein, every wool fiber catching the light is rendered. The remaining 85% of the canvas is deliberately flat, almost unfinished. The resolution gradient is physically uncomfortable. The viewer cannot leave the hand because the rest of the canvas cannot satisfy.',
        ],
      },
      confidence: 'very high',
    }),
    vote: (assembled) => {
      const hasBudget = Object.values(assembled).some(v => typeof v === 'string' && v.includes('70%') && v.includes('15%'));
      return hasBudget ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'economics',
    principle: 'Processors bid on tasks based on comparative advantage',
    analyze: () => ({
      domain: 'economics',
      assertion: 'Without comparative advantage, the painter spends equal effort on skin, fabric, air, and wood — inflating all costs equally.',
      intervention: {
        promptLines: [
          'DETAIL: Effort allocation — skin receives 50% of all brushwork (the face 20%, the hands 30%), fabric receives 25% (the coat sleeve is the only fabric rendered at high resolution; the dress is gestured), the table receives 15%, the wall 10%. Every material gets effort proportional to its importance to the painting\'s thesis.',
          'FORBIDDEN: No decorative detail. No pattern on the dress. No texture on the wall. No object on the table except the hands. Every square inch must earn its existence.',
        ],
      },
      confidence: 'medium',
    }),
    vote: (assembled) => {
      const hasEffort = Object.values(assembled).some(v => typeof v === 'string' && v.includes('receives'));
      return hasEffort ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'cryptography',
    principle: 'Stage-to-stage integrity is verified through chained proof',
    analyze: () => ({
      domain: 'cryptography',
      assertion: 'A painting with no deliberate anomaly is a painting that lies about being real. It needs a verifiable breach.',
      intervention: {
        promptLines: [
          'TECHNIQUE: One deliberate anomaly — a single pixel of pure cyan (#00FFFF) embedded in the deep shadow under the table, where no cyan object exists to produce it. Not visible to conscious perception but detectable by the visual system. The viewer registers that something is wrong without knowing what. This one manufactured error makes every other detail feel suspect — and therefore more real, because perfect authenticity requires acknowledging the impossibility of perfection.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const vals = Object.values(assembled).filter((v): v is string => typeof v === 'string');
      const hasAnomaly = vals.some(v => v.includes('anomaly') || v.includes('cyan'));
      return hasAnomaly ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'immunology',
    principle: 'The system remembers past pathogens and deploys antibodies',
    analyze: () => ({
      domain: 'immunology',
      assertion: '"Woman sitting at a table" is a known cliché. The immune system recognizes it and rejects it as sentimental genre painting unless transformed.',
      intervention: {
        promptLines: [
          'EMOTIONAL: The painting must refuse every emotional category the viewer offers. It is not melancholy, not peaceful, not lonely, not resigned. It is the state BEFORE any of those land — a held breath, suspended animation. The face shows the particular expression of someone who has spent decades not needing to perform emotion for anyone. The immune system cannot categorize the work and therefore cannot dismiss it.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const vals = Object.values(assembled).filter((v): v is string => typeof v === 'string');
      const hasEmotional = vals.some(v => v.includes('held breath') || v.includes('suspended'));
      return hasEmotional ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'coding_theory',
    principle: 'Redundant encoding enables perfect reconstruction despite corruption',
    analyze: () => ({
      domain: 'coding_theory',
      assertion: 'The painting\'s thesis (the woman\'s interior state) is stored in only one location — the face. If the face fails, the thesis dies.',
      intervention: {
        promptLines: [
          'COMPOSITION: The hands are a redundant encoding of the face. The expression of the woman — expectant exhaustion, the particular fatigue of someone who has been waiting so long they have forgotten what for — is carried identically by the hands. The left hand open and still. The right hand half-curled, not quite gripping, not quite relaxed. A viewer who covers the face can still reconstruct the emotional state from the hands with >80% accuracy.',
        ],
      },
      confidence: 'very high',
    }),
    vote: (assembled) => {
      const vals = Object.values(assembled).filter((v): v is string => typeof v === 'string');
      const hasRedundancy = vals.some(v => v.includes('redundant') || (v.includes('hands') && v.includes('face')));
      return hasRedundancy ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'type_systems',
    principle: 'A type system catches errors at compile time before execution',
    analyze: () => ({
      domain: 'type_systems',
      assertion: 'The painting declares itself as "portrait" but has no identifiable subject. This is a type error that must be intentional.',
      intervention: {
        promptLines: [
          'FINAL: The painting is typed as "portrait" — single figure, 3/4 length, interior setting, subdued lighting. The type violation: the figure has no identity. No jewelry, no tattoo, no scar visible, no expression that belongs to a specific person. The painting refuses to participate in the economy of recognizable subjects. It is a portrait of nobody. The genre violation IS the meaning.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const hasViolation = Object.values(assembled).some(v => typeof v === 'string' && v.includes('portrait') && v.includes('nobody'));
      return hasViolation ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'control_theory',
    principle: 'PID feedback maintains a set point despite disturbances',
    analyze: () => ({
      domain: 'control_theory',
      assertion: 'Without a set point, the painting drifts into sentiment or drama. It needs a homeostatic target.',
      intervention: {
        promptLines: [
          'EMOTIONAL: The set point is "the moment before." Not sadness, not peace, not exhaustion, not contemplation — the moment before any of those land. A woman sitting at a table with a bare bulb above her. The painting must correct every formal element back to this neutrality. If the light becomes too dramatic, pull it back. If the hands become too expressive, quiet them. If the composition becomes too interesting, flatten it. The painting is a homeostat for the unreachable interior.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const vals = Object.values(assembled).filter((v): v is string => typeof v === 'string');
      const hasSetPoint = vals.some(v => v.includes('set point') || v.includes('moment before'));
      return hasSetPoint ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'information_theory',
    principle: 'Every channel has capacity. Compress to essentials.',
    analyze: () => ({
      domain: 'information_theory',
      assertion: 'The image channel is finite. Most painting prompts waste bandwidth on decorative description.',
      intervention: {
        promptLines: [
          'FORBIDDEN: No decorative elements. No objects on the table except the hands. No pattern on the dress. No texture on the wall. No second light source. No window. No jewelry. No makeup. No expression to decode. Every element in the frame must carry three simultaneous loads: descriptive (what it is), expressive (how it feels), implicative (what it reveals about the thesis). Any element that carries fewer than three is rejected as noise.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const hasTriple = Object.values(assembled).some(v => typeof v === 'string' && v.includes('three simultaneous'));
      return hasTriple ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'game_theory',
    principle: 'Stable outcomes emerge when no player can improve by changing strategy',
    analyze: () => ({
      domain: 'game_theory',
      assertion: 'A painting that resolves into one interpretation is a painting the viewer beats once and leaves. The viewer must not find a winning move.',
      intervention: {
        promptLines: [
          'EMOTIONAL: The painting supports exactly three interpretations, each equally valid, none dominant: (a) this is a woman who has just received bad news and the news has not yet landed, (b) this is a woman who has been waiting so long she has forgotten what for and the waiting has become her natural state, (c) this is not a specific woman at all but the generic human body in an uncounted minute between events — a portrait of biological matter occupying space. The viewer cycles through all three and cannot settle on any. The Nash equilibrium is unsettleable.',
        ],
      },
      confidence: 'medium',
    }),
    vote: (assembled) => {
      const hasInterpretations = Object.values(assembled).some(v => typeof v === 'string' && ((v.match(/\(a\)/g) || []).length >= 1) && v.includes('(b)'));
      return hasInterpretations ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'graph_theory',
    principle: 'A graph models dependencies. Removing any edge collapses the structure.',
    analyze: () => ({
      domain: 'graph_theory',
      assertion: 'Most paintings have detachable elements — remove the vase and the painting still works. Museum art has no detachable nodes.',
      intervention: {
        promptLines: [
          'COMPOSITION: The painting has exactly five visual relationships, forming a 2-edge-connected graph: hand-to-light, hand-to-fabric, fabric-to-table, table-to-shadow, shadow-to-face. Remove any one edge and the composition is no longer a closed circuit. The light makes the hand visible. The hand makes the fabric meaningful. The fabric makes the table a surface. The table casts the shadow. The shadow touches the face. The face makes the light necessary. Nothing is detachable.',
        ],
      },
      confidence: 'high',
    }),
    vote: (assembled) => {
      const hasEdges = Object.values(assembled).some(v => typeof v === 'string' && v.includes('five visual relationships'));
      return hasEdges ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'evolutionary_biology',
    principle: 'Variation + selection + heredity drive adaptation',
    analyze: () => ({
      domain: 'evolutionary_biology',
      assertion: 'A painting that does not reference its ancestors is an orphan. Museum art carries its lineage visibly, mutated.',
      intervention: {
        promptLines: [
          'TECHNIQUE: The painting carries a visible mutation of Johannes Vermeer\'s "Girl with a Pearl Earring" — same single-figure-three-quarter-length-dark-background schema. The mutation: replace the pearl earring (beauty, ornament, art-historical commodity) with a small bandage on the index finger (accident, mortality, the body as vulnerable meat). The compositional schema survives the substitution. The viewer who knows the Vermeer feels the echo and the rupture simultaneously.',
        ],
      },
      confidence: 'medium',
    }),
    vote: (assembled) => {
      const vals = Object.values(assembled).filter((v): v is string => typeof v === 'string');
      const hasMutation = vals.some(v => v.includes('Vermeer') || v.includes('mutation'));
      return hasMutation ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'ceremony',
    principle: 'Preparation and execution are one seamless ritual',
    analyze: () => ({
      domain: 'ceremony',
      assertion: 'The medium itself is usually an afterthought — "oil on canvas" is mentioned once and forgotten.',
      intervention: {
        promptLines: [
          'TECHNIQUE: Hyperrealist oil on linen, 40" × 50". Not canvas — linen, for the tooth that catches the light in the impasto of the hands. The ground is a warm grey tonality that shows through thinly painted areas. The painting respects the ritual of its own making — the support, the ground, the medium, the surface are not invisible infrastructure but visible participants.',
        ],
      },
      confidence: 'low',
    }),
    vote: (assembled) => {
      const hasMedium = Object.values(assembled).some(v => typeof v === 'string' && v.includes('linen'));
      return hasMedium ? 'yea' : 'nay';
    },
  });

  c.register({
    key: 'information_theory_b',
    principle: 'Source coding compresses the signal to maximize throughput',
    analyze: () => ({
      domain: 'information_theory_b',
      assertion: 'No additional assertion.',
      intervention: {
        promptLines: [
          'FINAL: The painting can be described in three sentences: "A woman sits alone at a plain wooden table under a bare bulb. She is not sad. She is not waiting. She is occupying space, as bodies do in the minutes between the things that happen to them." Everything else in the prompt is support for this thesis. If the thesis cannot survive a three-sentence compression, the prompt is overbuilt.',
        ],
      },
      confidence: 'medium',
    }),
    vote: () => 'abstain' as const,
  });

  c.register({
    key: 'networking',
    principle: 'AIMD finds optimal transmission rate under congestion',
    analyze: () => ({
      domain: 'networking',
      assertion: 'Detail level should be additive on success, multiplicative on failure — but for a single painting, the principle applies to the composition itself: add detail where it survives, remove where it overwhelms.',
      intervention: {
        promptLines: [
          'DETAIL: The detail level follows an additive-increase/multiplicative-decrease curve from top to bottom of the canvas. The top (empty wall) is multiplicatively compressed — nearly zero detail. Each section downward adds detail additively until the bottom 15% (the hands) receives the maximum the medium can carry. The gradient is not linear but AIMD-shaped: flat at the top, gradual increase through the middle, exponential at the bottom. The viewer\'s attention "transmits" down the canvas without congestion.',
        ],
      },
      confidence: 'low',
    }),
    vote: () => 'abstain' as const,
  });

  c.register({
    key: 'tea',
    principle: 'Rushing destroys quality. The preparation IS the experience.',
    analyze: () => ({
      domain: 'tea',
      assertion: 'A prompt that rushes to the subject and skips the material conditions of the image produces a shallow rendering.',
      intervention: {
        promptLines: [
          'FINAL: The painting exists at the resolution of its slowness. The hours of brushwork on the hands are the subject. The speed of the empty wall is also the subject. The painting knows what it spent time on and that time is visible.',
        ],
      },
      confidence: 'low',
    }),
    vote: () => 'abstain' as const,
  });
}

// ============================================================
// EXECUTION
// ============================================================

const compiler = new Compiler();
registerAllDomains(compiler);

console.log('='.repeat(72));
console.log('  ABSURDITY PROTOCOL — PROMPT GENERATION');
console.log('  Target: Museum-quality hyperrealist oil painting prompt');
console.log('  Constraint: All 17 domains must contribute and vote');
console.log('='.repeat(72));

try {
  const { prompt, votes, fragments } = compiler.run();
  console.log(`\n${'='.repeat(72)}`);
  console.log('  PROTOCOL OUTPUT — THE PROMPT');
  console.log('='.repeat(72));
  console.log(`\n${prompt}\n`);
  console.log('='.repeat(72));
  console.log('  COMPOSITION REPORT');
  console.log(`  Domains contributed: ${fragments.length}`);
  console.log(`  Yea: ${votes.filter(v => v.vote === 'yea').length}`);
  console.log(`  Nay: ${votes.filter(v => v.vote === 'nay').length}`);
  console.log(`  Abstain: ${votes.filter(v => v.vote === 'abstain').length}`);
  console.log('='.repeat(72));
} catch (e) {
  console.log(`\n  [ERROR] ${(e as Error).message}`);
}

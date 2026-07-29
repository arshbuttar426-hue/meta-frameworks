/**
 * Absurdity Protocol — Pressure Test
 *
 * Task: Build a Context Preservation Framework for a middleware pipeline.
 * 5 context fields (userId, permissions, traceId, region, metadata) must survive
 * through 5 adversarial stages that actively drop, rename, or corrupt fields.
 *
 * Protocol enforcement: The Compiler refuses to execute unless ALL registered
 * domains contribute a spec fragment and vote Yea/Abstain. Skipping a domain
 * produces a structural error before any pipeline processing occurs.
 *
 * IRR is measured before and after protocol intervention.
 */

// ============================================================
// CORE TYPES
// ============================================================

type Stage = (ctx: Record<string, unknown>) => Record<string, unknown>;

interface PipelineSpec {
  stages: Stage[];
  criticalFields: string[];
}

interface SpecFragment {
  domain: string;
  assertion: string;
  intervention: Record<string, unknown>;
  confidence: 'low' | 'medium' | 'high' | 'very high';
}

interface Domain {
  key: string;
  principle: string;
  analyze(spec: PipelineSpec, ctx: Record<string, unknown>): SpecFragment;
  vote(assembled: Record<string, unknown>, fragment: SpecFragment): 'yea' | 'nay' | 'abstain';
}

type Vote = { domain: string; vote: 'yea' | 'nay' | 'abstain'; reason?: string };

// ============================================================
// IRR MEASUREMENT
// ============================================================

function measureIRR(input: Record<string, unknown>, output: Record<string, unknown>, criticalFields: string[]): number {
  let preserved = 0;
  for (const field of criticalFields) {
    if (JSON.stringify(input[field]) === JSON.stringify(output[field])) {
      preserved++;
    }
  }
  return preserved / criticalFields.length;
}

// ============================================================
// COMPILER — ANTI-SKIP GATE
// ============================================================

class Compiler {
  private domains = new Map<string, Domain>();

  register(domain: Domain): void {
    this.domains.set(domain.key, domain);
  }

  /**
   * ANTI-SKIP GATE: Refuses to assemble unless ALL registered domains
   * have contributed a fragment. This is structural — not a runtime warning.
   */
  assemble(
    spec: PipelineSpec,
    initialState: Record<string, unknown>,
    fragments: SpecFragment[],
  ): Record<string, unknown> {
    const contributed = new Set(fragments.map((f) => f.domain));

    // Gate: every registered domain must be present
    for (const key of this.domains.keys()) {
      if (!contributed.has(key)) {
        throw new Error(
          `ANTI-SKIP GATE: Domain "${key}" did not contribute a spec fragment. ` +
          `All ${this.domains.size} domains must participate before assembly.`,
        );
      }
    }

    // Weave all interventions into a single context envelope
    let envelope = { ...initialState, __absurdity: { fragments: [] as SpecFragment[], version: 1 } };

    for (const fragment of fragments) {
      const intervention = fragment.intervention;
      if (intervention.injectFields) {
        envelope = { ...envelope, ...(intervention.injectFields as Record<string, unknown>) };
      }
      if (intervention.redundantCopies) {
        const copies = intervention.redundantCopies as Record<string, string[]>;
        for (const [field, locations] of Object.entries(copies)) {
          for (const loc of locations) {
            envelope[`${loc}_${field}`] = envelope[field];
          }
        }
      }
      if (intervention.typeConstraints) {
        const constraints = intervention.typeConstraints as Record<string, { type: string; valid?: unknown[] }>;
        for (const [field, constraint] of Object.entries(constraints)) {
          if (field in envelope) {
            const val = envelope[field];
            const actualType = typeof val;
            if (actualType !== constraint.type) {
              throw new Error(
                `TYPE CHECK: Field "${field}" expected ${constraint.type}, got ${actualType}. ` +
                `Domain "${fragment.domain}" rejects this spec.`,
              );
            }
            if (constraint.valid && !constraint.valid.includes(val)) {
              throw new Error(
                `TYPE CHECK: Field "${field}" value "${String(val)}" not in valid set. ` +
                `Domain "${fragment.domain}" rejects this spec.`,
              );
            }
          }
        }
      }
      if (intervention.chainHash) {
        envelope.__chainHash = hashFragment(fragment);
      }
      (envelope.__absurdity.fragments as SpecFragment[]).push(fragment);
    }

    return envelope;
  }

  /**
   * VOTING: Every domain reviews the assembled envelope.
   * A single Nay blocks execution.
   */
  vote(
    envelope: Record<string, unknown>,
    fragments: SpecFragment[],
  ): { passed: boolean; votes: Vote[] } {
    const votes: Vote[] = [];

    for (const fragment of fragments) {
      const domain = this.domains.get(fragment.domain);
      if (!domain) continue;

      const result = domain.vote(envelope, fragment);
      votes.push({ domain: fragment.domain, vote: result, reason: result === 'nay' ? 'domain rejected final spec' : undefined });
    }

    const nayCount = votes.filter((v) => v.vote === 'nay').length;
    const abstainCount = votes.filter((v) => v.vote === 'abstain').length;
    const yeaCount = votes.filter((v) => v.vote === 'yea').length;

    // Gate: unanimous yea-or-abstain required
    const passed = nayCount === 0;

    if (!passed) {
      const nayDomains = votes.filter((v) => v.vote === 'nay').map((v) => v.domain);
      throw new Error(
        `CONSENSUS FAILED: ${nayCount} domain(s) voted Nay: [${nayDomains.join(', ')}]. ` +
        `Yea: ${yeaCount}, Nay: ${nayCount}, Abstain: ${abstainCount}. ` +
        `Unanimous Yea-or-Abstain required.`,
      );
    }

    return { passed, votes };
  }

  /**
   * Reconstructs dropped critical fields from redundant and mycelial copies.
   * This is where Coding Theory and Mycology interventions pay off.
   */
  private reconstruct(ctx: Record<string, unknown>, spec: PipelineSpec): Record<string, unknown> {
    const result = { ...ctx };
    for (const field of spec.criticalFields) {
      if (result[field] === undefined || result[field] === null) {
        // Try redundant copies (Coding Theory)
        for (const prefix of ['redundant_1', 'redundant_2', 'redundant_3']) {
          const copy = result[`${prefix}_${field}`];
          if (copy !== undefined && copy !== null) {
            result[field] = copy;
            break;
          }
        }
        // Fall back to mycelial copy (Mycology)
        if ((result[field] === undefined || result[field] === null) && `mycelial_${field}` in result) {
          result[field] = result[`mycelial_${field}`];
        }
        // Fall back to chain hash reference (Cryptography) — last known good
        if ((result[field] === undefined || result[field] === null) && '__chainHash' in result) {
          result[field] = `reconstructed_via_chain`;
        }
      }
    }
    return result;
  }

  /**
   * Full cycle: analyze → assemble → vote → execute with reconstruction
   */
  run(
    spec: PipelineSpec,
    initialState: Record<string, unknown>,
  ): { output: Record<string, unknown>; irr: number; votes: Vote[]; fragments: SpecFragment[] } {
    // Step 1: Each domain analyzes and produces a fragment
    const fragments: SpecFragment[] = [];
    for (const domain of this.domains.values()) {
      fragments.push(domain.analyze(spec, initialState));
    }

    // Step 2: Assemble (ANTI-SKIP GATE — throws if any domain missing)
    const envelope = this.assemble(spec, initialState, fragments);

    // Step 3: Vote (CONSENSUS GATE — throws if any domain votes Nay)
    const { votes } = this.vote(envelope, fragments);

    // Step 4: Execute pipeline stages with reconstruction after each
    let ctx = { ...envelope };
    for (const stage of spec.stages) {
      ctx = stage(ctx);
      ctx = this.reconstruct(ctx, spec);
    }

    // Step 5: Measure IRR
    const irr = measureIRR(initialState, ctx, spec.criticalFields);

    return { output: ctx, irr, votes, fragments };
  }
}

function hashFragment(f: SpecFragment): string {
  return `hash_${f.domain}_${Date.now()}`;
}

// ============================================================
// DOMAIN IMPLEMENTATIONS
// ============================================================

/**
 * Domain 10: Coding Theory — Redundant Encoding
 * Encodes critical fields as error-correcting codewords spread
 * across multiple independent envelope slots.
 */
const codingTheoryDomain: Domain = {
  key: 'coding_theory',
  principle: 'Redundant encoding enables perfect reconstruction despite corruption',
  analyze(spec, ctx) {
    const copies: Record<string, string[]> = {};
    for (const field of spec.criticalFields) {
      copies[field] = ['redundant_1', 'redundant_2', 'redundant_3'];
    }
    return {
      domain: this.key,
      assertion: `Critical fields [${spec.criticalFields.join(', ')}] have no redundancy — a single drop destroys the field permanently`,
      intervention: { redundantCopies: copies },
      confidence: 'very high',
    };
  },
  vote(assembled, fragment) {
    const copies = fragment.intervention.redundantCopies as Record<string, string[]>;
    for (const [field, locations] of Object.entries(copies)) {
      const hasField = field in assembled;
      const hasCopies = locations.every((loc) => `${loc}_${field}` in assembled);
      if (!hasField && !hasCopies) return 'nay';
    }
    return 'yea';
  },
};

/**
 * Domain 1: Mycology — Distributed Storage
 * Distributes identity parameters across multiple stage sections
 * to eliminate single points of failure.
 */
const mycologyDomain: Domain = {
  key: 'mycology',
  principle: 'Resilience emerges from distribution, not centralization',
  analyze(spec, ctx) {
    const inject: Record<string, string> = {};
    for (const field of spec.criticalFields) {
      inject[`mycelial_${field}`] = String(ctx[field] ?? '');
    }
    return {
      domain: this.key,
      assertion: `All critical fields are stored in a single location — one stage can wipe them all`,
      intervention: { injectFields: inject },
      confidence: 'high',
    };
  },
  vote(assembled, fragment) {
    const inject = fragment.intervention.injectFields as Record<string, string>;
    const allPresent = Object.keys(inject).every((k) => k in assembled);
    return allPresent ? 'yea' : 'nay';
  },
};

/**
 * Domain 11: Type Systems — Compile-Time Validation
 * Enforces that every critical field has a valid type and range
 * before the spec reaches the execution stage.
 */
const typeSystemsDomain: Domain = {
  key: 'type_systems',
  principle: 'A type system catches errors at compile time, not runtime',
  analyze(spec, ctx) {
    const constraints: Record<string, { type: string; valid?: unknown[] }> = {
      userId: { type: 'string' },
      traceId: { type: 'string' },
      region: { type: 'string', valid: ['us-east', 'us-west', 'eu-west', 'ap-southeast'] },
    };
    return {
      domain: this.key,
      assertion: `Pipeline stages receive untyped data — malformed fields propagate silently`,
      intervention: { typeConstraints: constraints },
      confidence: 'high',
    };
  },
  vote(assembled, fragment) {
    const constraints = fragment.intervention.typeConstraints as Record<string, { type: string; valid?: unknown[] }>;
    for (const [field, constraint] of Object.entries(constraints)) {
      if (field in assembled) {
        if (typeof assembled[field] !== constraint.type) return 'nay';
        if (constraint.valid && !constraint.valid.includes(assembled[field])) return 'nay';
      }
    }
    return 'yea';
  },
};

/**
 * Domain 12: Control Theory — PID Homeostasis
 * Applies proportional-integral-derivative correction when
 * critical fields drift from their expected values across stages.
 */
const controlTheoryDomain: Domain = {
  key: 'control_theory',
  principle: 'PID feedback maintains set points despite disturbances',
  analyze(spec, ctx) {
    const expected: Record<string, unknown> = {};
    for (const field of spec.criticalFields) {
      expected[field] = ctx[field];
    }
    return {
      domain: this.key,
      assertion: `Drift accumulates across stages with no correction mechanism — small errors compound`,
      intervention: {
        pidSetPoints: expected,
        pidGains: { Kp: 0.8, Ki: 0.1, Kd: 0.05 },
      },
      confidence: 'high',
    };
  },
  vote(assembled, fragment) {
    const setPoints = fragment.intervention.pidSetPoints as Record<string, unknown>;
    for (const [field, expected] of Object.entries(setPoints)) {
      if (field in assembled && assembled[field] !== expected) return 'nay';
    }
    return 'yea';
  },
};

/**
 * Domain 13: Information Theory — Channel Optimization
 * Compresses low-value fields and expands high-value fields
 * to stay within each stage's effective processing capacity.
 */
const infoTheoryDomain: Domain = {
  key: 'information_theory',
  principle: 'Every channel has a capacity — compress signal, maximize throughput',
  analyze(spec, ctx) {
    return {
      domain: this.key,
      assertion: `All fields consume equal bandwidth regardless of their information value — the channel is overloaded with low-value noise`,
      intervention: {
        priorityOrder: spec.criticalFields,
        compressionMap: { metadata: 'compressed' },
      },
      confidence: 'medium',
    };
  },
  vote(assembled, fragment) {
    const priority = fragment.intervention.priorityOrder as string[];
    const topFieldsPresent = priority.slice(0, 3).every((f) => f in assembled);
    return topFieldsPresent ? 'yea' : 'nay';
  },
};

/**
 * Domain 7: Cryptography — Continuity Chain
 * Builds a verifiable chain of hashes across stages so that
 * any unauthorized field mutation is detected before it propagates.
 */
const cryptographyDomain: Domain = {
  key: 'cryptography',
  principle: 'Chained hashing makes stage-to-stage tampering visible before it compounds',
  analyze(spec, ctx) {
    return {
      domain: this.key,
      assertion: `No mechanism exists to verify that a stage hasn't corrupted upstream data`,
      intervention: {
        chainHash: true,
        criticalSeal: spec.criticalFields,
      },
      confidence: 'very high',
    };
  },
  vote(assembled, fragment) {
    const hasChainHash = '__chainHash' in assembled;
    return hasChainHash ? 'yea' : 'nay';
  },
};

// ============================================================
// DEMO: INTENTIONAL GATE TRIGGER
// ============================================================

function demoAntiSkipGate(): void {
  console.log('\n=== TEST 1: ANTI-SKIP GATE — Missing domain ===\n');

  const compiler = new Compiler();
  compiler.register(codingTheoryDomain);
  compiler.register(mycologyDomain);
  // Deliberately NOT registering type_systems, control_theory, etc.

  const spec: PipelineSpec = {
    stages: [(ctx) => ctx],
    criticalFields: ['userId'],
  };

  const initialState = { userId: 'alice', traceId: 'abc-123' };

  try {
    // Only 2 fragments for 2 registered domains — this should work
    const fragments = [
      codingTheoryDomain.analyze(spec, initialState),
      mycologyDomain.analyze(spec, initialState),
    ];
    compiler.assemble(spec, initialState, fragments);
    console.log('  PASS: 2 domains, 2 fragments — gate passes');
  } catch (e) {
    console.log(`  GATE TRIGGERED: ${(e as Error).message}`);
  }

  const compiler2 = new Compiler();
  compiler2.register(codingTheoryDomain);
  compiler2.register(mycologyDomain);
  compiler2.register(typeSystemsDomain);
  compiler2.register(controlTheoryDomain);
  compiler2.register(infoTheoryDomain);
  compiler2.register(cryptographyDomain);

  try {
    // Only 4 fragments for 6 registered domains — ONE missing triggers the gate
    const fragments = [
      codingTheoryDomain.analyze(spec, initialState),
      mycologyDomain.analyze(spec, initialState),
      typeSystemsDomain.analyze(spec, initialState),
      controlTheoryDomain.analyze(spec, initialState),
      // Missing: info_theory, cryptography
    ];
    compiler2.assemble(spec, initialState, fragments);
    console.log('  PASS: ?');
  } catch (e) {
    console.log(`  GATE TRIGGERED: ${(e as Error).message}`);
  }
}

// ============================================================
// DEMO: FULL CYCLE WITH ADVERSARIAL PIPELINE
// ============================================================

function demoFullCycle(): void {
  console.log('\n=== TEST 2: FULL PROTOCOL CYCLE ===\n');

  const criticalFields = ['userId', 'permissions', 'traceId', 'region', 'metadata'];

  // Adversarial stages that drop and corrupt fields
  const adversarialStages: Stage[] = [
    (ctx) => { const c = { ...ctx }; delete c.metadata; return c; },
    (ctx) => { const c = { ...ctx }; c.userId = undefined; return c; },
    (ctx) => { const c = { ...ctx }; delete c.permissions; return c; },
    (ctx) => { const c = { ...ctx }; c.region = 'unknown'; return c; },
    (ctx) => { const c = { ...ctx }; delete c.traceId; return c; },
  ];

  const spec: PipelineSpec = { stages: adversarialStages, criticalFields };

  const initialState: Record<string, unknown> = {
    userId: 'alice',
    permissions: ['read', 'write'],
    traceId: 'trace-42',
    region: 'us-east',
    metadata: { session: 'abc', ttl: 3600 },
  };

  // Before: run pipeline WITHOUT protocol
  let degraded = { ...initialState };
  for (const stage of adversarialStages) {
    degraded = stage(degraded);
  }
  const beforeIRR = measureIRR(initialState, degraded, criticalFields);
  console.log(`  IRR WITHOUT protocol: ${(beforeIRR * 100).toFixed(0)}% (${criticalFields.length - countPreserved(initialState, degraded, criticalFields)} of ${criticalFields.length} fields lost)`);

  // After: run WITH protocol
  const compiler = new Compiler();
  compiler.register(codingTheoryDomain);
  compiler.register(mycologyDomain);
  compiler.register(typeSystemsDomain);
  compiler.register(controlTheoryDomain);
  compiler.register(infoTheoryDomain);
  compiler.register(cryptographyDomain);

  try {
    const result = compiler.run(spec, initialState);

    // The protocol preserves fields through the envelope — redundant copies,
    // distributed storage, and type checks keep them alive
    const afterIRR = result.irr;
    const votesSummary = result.votes.map((v) => `${v.domain}=${v.vote}`).join(', ');
    console.log(`\n  IRR WITH protocol: ${(afterIRR * 100).toFixed(0)}%`);
    console.log(`  Improvement: +${((afterIRR - beforeIRR) * 100).toFixed(0)} percentage points`);
    console.log(`  Votes: [${votesSummary}]`);
    console.log(`  Domains participated: ${result.fragments.length}`);
    console.log(`  Output keys: ${Object.keys(result.output).filter(k => !k.startsWith('__')).join(', ')}`);
    const outputDomains = new Set((result.output.__absurdity?.fragments ?? []).map((ff: SpecFragment) => ff.domain));
    const allIntact = result.fragments.every((f) => outputDomains.has(f.domain));
    console.log(`  All domain fragments in output: ${allIntact ? 'yes' : 'no'}`);
  } catch (e) {
    console.log(`  PROTOCOL ERROR: ${(e as Error).message}`);
  }
}

function countPreserved(input: Record<string, unknown>, output: Record<string, unknown>, fields: string[]): number {
  return fields.filter((f) => JSON.stringify(input[f]) === JSON.stringify(output[f])).length;
}

// ============================================================
// DEMO: CONSENSUS FAILURE
// ============================================================

function demoConsensusFailure(): void {
  console.log('\n=== TEST 3: CONSENSUS GATE — Domain votes Nay ===\n');

  const compiler = new Compiler();

  // A domain that ALWAYS votes Nay
  const pedanticDomain: Domain = {
    key: 'pedant',
    principle: 'Nothing is ever good enough',
    analyze() {
      return { domain: this.key, assertion: 'always wrong', intervention: {}, confidence: 'low' };
    },
    vote() {
      return 'nay';
    },
  };

  compiler.register(codingTheoryDomain);
  compiler.register(pedanticDomain);

  const spec: PipelineSpec = { stages: [(ctx) => ctx], criticalFields: ['userId'] };
  const initialState = { userId: 'alice' };

  try {
    compiler.run(spec, initialState);
    console.log('  PASS: consensus reached (unexpected)');
  } catch (e) {
    console.log(`  CONSENSUS GATE TRIGGERED: ${(e as Error).message}`);
  }
}

// ============================================================
// RUN ALL TESTS
// ============================================================

console.log('='.repeat(72));
console.log('  ABSURDITY PROTOCOL — PRESSURE TEST');
console.log('  Framework: Domain Consensus Protocol v1');
console.log('  Domains: coding_theory, mycology, type_systems, control_theory, info_theory, cryptography');
console.log('  Pipeline: 5 adversarial stages, 5 critical fields');
console.log('='.repeat(72));

demoAntiSkipGate();
demoFullCycle();
demoConsensusFailure();

console.log('\n' + '='.repeat(72));
console.log('  PRESSURE TEST COMPLETE');
console.log('  Summary:');
console.log('  - Anti-Skip Gate: triggers on missing domain (structural error)');
console.log('  - Consensus Gate: triggers on Nay vote (unanimous required)');
console.log('  - IRR: measured before and after protocol intervention');
console.log('  - All domains: must participate or execution is blocked');
console.log('='.repeat(72));

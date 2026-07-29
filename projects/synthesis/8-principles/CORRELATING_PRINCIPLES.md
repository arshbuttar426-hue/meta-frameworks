# Correlating Principles for the Cinematic Prompt Engine

## Principle 1: Department Isolation (The Core Invariant)
**Every department has exactly one responsibility. Departments never invent intention — they execute it.**
- Cinema: Director sets intent → Camera observes → Editor paces → Compiler assembles
- Absurdity: MycelialRouter distributes to specialist nodes; no central summarizer
- Microcosmos: Each of 12 Books has exclusive domain; Producer checks cross-Book conflicts
- **Rule**: A department's output must be a subset of its inputs (no hallucinated specs). Every transformation must be invertible at the audit level.

## Principle 2: Structured Over Prose (The Compiler is NOT a Writer)
**The Prompt Compiler is a lossless template filler, not a creative writer. The model sees organized structure, not summarized paragraphs.**
- Supporting data: IRR improves from 0.34 → 0.89 when compiler temperature drops from 1.5 → 0.3
- Absurdity protocol: Dimension-sorted arrays `[CAMERA]`, `[CHARACTER]`, `[LIGHTING]` preserve structured fields
- Microcosmos: `render_prompt` must follow Veo 3.1 template — every section maps to a Book output
- Microcosmos anomaly: Book XII says "complete coverage" but has no enforcement mechanism
- **Rule**: The Compiler fills templates; it does not write prose. Every structured field must survive to the model unchanged.

## Principle 3: Physics-Based Continuity (No Teleportation)
**The camera is a physical object in 3D space. Focus is a dependent variable of position. Character identity is a lock, not a suggestion.**
- Microcosmos: Icosahedral geodesic arcs, C² acceleration, df/dt = v·cos(θ), no teleportation
- Absurdity: CreativeInertia tracks momentum state (value, velocity, mass, streak); high-mass properties resist change
- CharacterDNA: 13-trait genome appended verbatim to every prompt
- ContinuityHomeostat: measure → detect deviation → correct; tolerance=0 for identity
- **Rule**: Focus follows camera position. Character appearance is zero-tolerance. Every frame continues from the previous — explicitly state what changed.

## Principle 4: Information Is a Budget (Spend Wisely)
**Every prompt component consumes from a fixed budget of model capacity and token space. Budget allocation must be explicit.**
- CLIP: 77-token hard limit. Prioritize: character > lighting > spatial > camera
- Absurdity: Entropy budgeting — CharacterDNA 40%, Environment 25%, Camera 15%, Lighting 15%, Action 5%
- MODELTUNE: Model selection by task — Gemma for high-complexity, Phi for fast code, T=0.3 for precision
- **Rule**: Know the token limit. Budget by entropy cost. When exceeded, demote to shorthand (don't drop).

## Principle 5: Every Insight Terminates in Code (The Specificity Mandate)
**Philosophical insights without deployment plans are forbidden. Every principle must specify: file, class, interface, call site, tests.**
- Absurdity: Specificity Engine rejects vague statements. Force-Down Protocol (6 steps) from principle → artifact.
- MODELTUNE: Every domain implementation has complete Python code with interfaces and test cases.
- Microcosmos: Anomalies have specific remedies (e.g., "Add `position: [x, y, z]` field, update `scene_template.yaml` line 42").
- **Rule**: If you can't name the file, the function, the call site, and three test cases — you don't have a solution yet.

## Principle 6: Conflict Detection Is Explicit (Not Faith-Based)
**Cross-department conflicts must be detected at merge time, not assumed away.**
- Microcosmos: Producer's `conflicts_resolved` was always "none" — exposed as Anomaly CROSS-3. Now requires structured checks: `director_vs_camera_visibility: PASS|CONFLICT`, etc.
- Cinema: Book XII (Producer) is the merge authority — but every existing scene had zero reported conflicts
- Absurdity: ContinuityHomeostat corrects drift; ImmuneMemory recognizes recurring drift patterns
- **Rule**: Every merge must list checked domains with PASS/CONFLICT verdicts. "No conflicts" must be proven, not asserted.

## Principle 7: The Model Has No Memory — You Are Its Memory
**The generative model sees each frame as a newborn universe. The pipeline must embed persistence in every prompt.**
- Absurdity: WorldSchema adds `[PERSISTS: ...]` clauses; CharacterDNA is embedded verbatim; Merkle continuity chains hash frame state
- Microcosmos: `memory.yaml` persists facts across scenes; `symbols_active` registry (Anomaly CROSS-4 — unresolved)
- Cinema: ContinuityVerdict is generated per-segment with character locks, camera locks, environment locks
- **Rule**: Every prompt must include: character identity (compact genome), persistence notes (off-screen objects), continuity verdict (what changed, what stayed), correction clauses (if drift detected).

## Principle 8: Temperature Is Architecture-Dependent (One Size Does NOT Fit All)
**Model architecture determines optimal temperature range. Direct models (Phi, Gemma) work at any temp. Thinking models need high temp to function.**
- Critical finding: Compiler must run at T=0.3 for lossless field preservation
- Zone assignments: Creative zones T=0.7, Technical zones T=0.3, Identity zones deterministic (no LLM)
- **Rule**: Know your model's phase boundaries. Don't use thinking models (VibeThinker, Qwen) for compiler tasks. Gemma-12B is the gold standard for reliability.

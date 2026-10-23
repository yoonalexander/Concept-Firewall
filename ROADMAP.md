# Concept Firewall Roadmap

**Updated:** October 23, 2026

**Project:** Reproducible research on predicting and recovering from NCM generation errors.

**Current position:** Initial M0–M3 implementation, bounded follow-up, scoped negative-result closeout, and reproducibility packaging completed; the M3 continuation gate has not passed.

**Current package version:** `0.1.1`, tagged `sudoku-study-v0.1.1`. This scoped software package does not imply completion of the later evidence targets below.

This file is the project execution roadmap. The [original design document](Concept_Firewall_Design_Document.md) remains the scientific specification; the [design review](docs/design_review.md) and [experiment protocol](docs/experiment_protocol.md) explain implementation decisions. Future phases remain part of the roadmap even while their prerequisites are unmet.

## 1. What the project must establish

The research progresses through three separate questions:

1. **Prediction:** Can an intermediate state predict the final correctness of its trajectory on unseen puzzles?
2. **Recoverability:** Under an explicitly stochastic continuation policy, can alternative suffixes recover from the same frozen prefix?
3. **Intervention:** Can a live policy improve correctness at the same measured total computation budget?

Sudoku is the first exact-verifiable reliability benchmark. Natural-language factuality is a later extension. Neither a Sudoku detector nor an observational probe establishes production safety, causal mechanisms, or inference savings.

## 2. Phase and milestone map

The design's experiment phases and engineering milestones use different numbering. **M3 means offline probes; Phase 3 means prefix branching.** Use the mapping below when selecting work.

| Experiment phase | Milestone | Purpose | Current status |
|---|---|---|---|
| Phase 0 | M0 — Reproduce | Run the official hard-Sudoku baseline with recorded provenance | Initial scope completed |
| Phase 1 | M1 — Observe | Capture full-size cumulative prefix representations and candidate boards | Initial scope completed |
| Phase 1 | M2 — Label | Verify Sudoku outputs and analyze correctness transitions | Implemented, independently checked and agent spot-checks recorded |
| Phase 2 | M3 — Probe | Evaluate failure prediction against strong controls | Initial experiment and bounded follow-up completed; continuation criteria not met |
| Phase 3 | M4 — Branch | Resume from frozen prefixes and sample alternative suffixes | Planned; gated |
| Phase 4 | M5 — Intervene | Benchmark live policies against equal-cost alternatives | Planned; gated |
| Phase 5 | M6 — Generalize | Evaluate source-grounded translation and summarization errors | Planned stretch extension |
| Phase 6 | M7 — Visualize | Build an optional research trajectory explorer | Optional; gated |
| Cross-cutting closeout | Research release | Package the declared study, reproducible evidence, and limitations | Scoped Sudoku study packaged with verified evidence replay; v1.0 milestone not claimed |

**Status rule:** completing an implementation or experiment does not mean its hypothesis succeeded. A negative result can complete an experiment while preventing dependent research phases from starting.

## 3. Current evidence

- The official evaluator solved **1,725/2,000 hard-Sudoku puzzles (86.25%)** on the recorded local environment. This does not claim an exact match to a paper's hardware/runtime protocol.
- Corrected collection produced **24,000 records**, covering all 12 levels for 2,000 unique puzzles. Every final reconstruction matches the official baseline.
- The recorded verification run passed **74 tests and 119 subtests**. Five saved primary-level probe families also reproduced their 400 held-out probabilities and passed the training-scaler audit.
- Four internal puzzle partitions contain 1,000 training, 300 validation, 300 calibration, and 400 test puzzles. They carve up the public official test dataset; they are not an untouched official probe benchmark.
- At the prespecified level 6, adding pooled latents to the input-plus-decoded control changed AUROC by **−0.0078**, with a paired puzzle-bootstrap 95% interval of **[−0.0368, +0.0193]**. Useful incremental prediction was not demonstrated.
- Initial direct decoding of short upstream `z_levels` was unsuitable for full-board comparisons. Those experiments are explicitly superseded; the corrected implementation snapshots the full cumulative prefix without future-state aliasing.
- On October 23, an independent checker matched all 24,000 current labels and 2,000 final outcomes. The [agent case walkthrough](results/reports/m3_manual_case_review.md) now records the manual spot checks. Updated verification passed **87 tests and 119 subtests**.
- The [bounded spatial follow-up](results/reports/m3_followup_evaluation.md) used 1,600 development puzzles only, excluding the old 400-puzzle test partition. Neither of two fixed spatial variants met the primary candidate criteria; at level 11, adding spatial features reduced performance relative to the decoded-board control. The checked official hard release has no unused split for fresh confirmation.
- The [current Sudoku study is closed with a negative report](results/reports/sudoku_study_closeout.md). This closes the selected experiment, not the remaining M4–M7 roadmap.

Evidence: [baseline](results/reports/baseline_reproduction.md), [corrected trajectories](results/reports/level_trajectory_analysis.md), [probe evaluation](results/reports/probe_evaluation.md), [limitations](results/reports/negative_results_and_limitations.md), and [reconstruction correction](results/reports/reconstruction_correction.md).

## 4. Phase 0 — Reproduce the official baseline (M0)

**Objective:** establish that the actual released model, data, environment, and evaluator work before interpreting custom experiments.

**Initial deliverables completed:**

- [x] Pin unmodified NCM source and record its MIT license, exact commit, and compatibility assumptions.
- [x] Set up an isolated CUDA environment and record software/hardware information.
- [x] Download only the necessary hard-Sudoku artifacts; verify immutable revisions and file digests.
- [x] Run the official 32-puzzle smoke evaluation, then the full 2,000-puzzle evaluation.
- [x] Preserve commands, raw predictions/logs, manifests, configuration, and documented deviations.

**Gate:** the official checkpoints load and produce actual outputs; discrepancies and environment deviations are documented. For this local reproduction, that gate passed. Repeat the relevant checks when source, weights, data, hardware, or generation settings change.

**Primary artifact:** [baseline reproduction report](results/reports/baseline_reproduction.md).

## 5. Phase 1 — Observe trajectories and label outcomes (M1–M2)

**Objective:** create trustworthy observational data without changing generation or leaking final outcomes into earlier features.

**M1 — Observation, initial deliverables completed:**

- [x] Capture all 12 code prefixes, pooled cumulative tokenizer latents, and decoded candidate boards.
- [x] Snapshot full-size cumulative prefixes using upstream accumulation behavior; clone before later levels mutate the accumulator.
- [x] Verify full sequence length, separate snapshot storage, independence from future code mutations, and final-output equivalence.
- [x] Save versioned JSONL/Parquet observations with content-based puzzle identities and separate final outcomes.
- [x] Record synchronized generation totals and post-hoc collection costs separately.

**M2 — Labels and analysis:**

- [x] Implement strict format, completeness, clue, row, column, and subgrid checks; accept alternative valid solutions.
- [x] Test malformed outputs, blanks, Unicode lookalikes, changed clues, conflicts, and upstream token formatting.
- [x] Keep current-level correctness distinct from eventual final correctness.
- [x] Produce correctness-by-level plots and transition summaries; preserve superseded evidence with explanations.
- [x] Record a separate agent walkthrough of representative successful, failed, malformed, and intermediate cases against raw inputs/outputs. See the [case review](results/reports/m3_manual_case_review.md); it is not independent human annotation.

**Gate:** all expected levels are present, final outputs match the official baseline, labels are trustworthy, and no future information reaches earlier features. Automated and independently implemented full-data checks passed; agent case-review witnesses are recorded.

**Timing boundary:** collection is post-hoc. Incremental generator timings and actual online remaining time are still unknown. An instrumentation-overhead comparison requires a controlled measurement, not a subtraction of unrelated runs or a count of skipped levels.

**Primary artifacts:** [trajectory analysis](results/reports/level_trajectory_analysis.md), the corrected collection manifest, and the [reproduction log](docs/reproduction_log.md).

## 6. Phase 2 — Test early failure prediction (M3)

**Objective:** determine whether internal representations add useful predictive information beyond puzzle difficulty and partial-board diagnostics.

**First experiment completed:**

- [x] Freeze exact puzzle-level train/validation/calibration/test partitions before fitting.
- [x] Compare prevalence, level-only, categorical raw-input, decoded-board, code-frequency, pooled-latent, combined, and shuffled-training-label controls.
- [x] Fit preprocessing and regularized linear probes on training puzzles only; select regularization on validation puzzles.
- [x] Fit probability calibration and empirical false-positive thresholds on calibration puzzles only.
- [x] Report held-out AUROC, average precision, Brier score, false positives, recall, reliability bins, class counts, and puzzle-bootstrap uncertainty.
- [x] Audit saved probe predictions and training-only scaler statistics; disclose all evaluated levels and models.
- [x] Record the negative primary comparison and stop automatic progression to more complex systems.

**Continuation gate:** demonstrate a prespecified, practically meaningful incremental benefit over appropriate input-only and decoded-output controls on suitably held-out puzzles, with uncertainty and a useful operating point. **The current experiment did not pass this gate.** A secondary peak or final-level diagnostic score does not satisfy it.

**Bounded follow-up completed October 23:** [audit and evaluation](results/reports/m3_followup_evaluation.md). Labels and calibration were audited; two frozen, 256-dimensional row/cell spatial representations were evaluated once using nested grouped development folds. Neither met the declared primary criteria. The old 400-puzzle test partition was excluded from new feature capture and fitting. No fresh confirmatory split was found in the checked official hard release. Work stopped after the fixed comparison.

**Unselected future research options, requiring a new scope and protocol:**

- Extend the completed overfitting/calibration diagnosis only if a separately justified study warrants it.
- Complete the full Sudoku symmetry/overlap audit and obtain suitable fresh confirmation data; the current test outcomes are exposed. The completed limited audit covered digit renaming and transpose only.
- Compare alternative spatial pooling, frozen codebook embeddings, or selected transformer activations under controlled memory and timing costs.
- Consider low-capacity nonlinear or history-based probes only with a declared rationale and matched baselines.
- Predeclare a new protocol, primary comparison, success margin, uncertainty method, false-alarm target, and compute limit before fitting a follow-up study.
- Where relevant, evaluate the probability of any false alarm over the whole trajectory, not only a single-level FPR.

These are research options, not a promise that a better detector exists. Repeated tuning against the current test set must not be presented as fresh held-out evidence.

**Primary artifacts:** [probe report](results/reports/probe_evaluation.md), [frozen protocol](configs/probe_protocol.json), saved probes, split manifests, artifact audit, and limitations report.

## 7. Phase 3 — Measure recoverability with prefix branching (M4)

**Objective:** estimate failure probability across alternative continuations from the same frozen prefix, separately from predicting one trajectory's outcome.

**Entry condition:** useful M3 evidence, or a separately justified study in which recoverability itself is valuable. The existing negative result does not automatically authorize custom continuation work.

**Planned deliverables:**

- [ ] Define and document the continuation state needed at a selected prefix, including RNG state and relevant cached model state.
- [ ] Add a minimal wrapper or isolated upstream patch for resumption; preserve unmodified baseline behavior.
- [ ] Prove resumed continuation matches uninterrupted generation under identical state/settings where equivalence is supported.
- [ ] Freeze and hash the prefix; demonstrate no branch changes earlier codes.
- [ ] Sample suffixes with an explicit nonzero-temperature policy, recorded seeds, top-k/top-p settings, and branch counts.
- [ ] Estimate conditional failure frequencies with uncertainty and compare recoverability predictions to cheap controls.
- [ ] Record branch GPU work, latency, memory, and all failed attempts.

**Gate:** frozen-prefix and resume-equivalence tests pass, branches are reproducible and genuinely stochastic, and uncertainty/cost are reported. Repeating the temperature-zero default is not a branching experiment. Compare stochastic policies separately from the deterministic published configuration.

**Planned artifacts:** branching configuration, continuation tests, prefix/branch records, and `results/reports/counterfactual_recoverability.md`.

## 8. Phase 4 — Benchmark live interventions (M5)

**Objective:** test whether acting on predictions improves correctness at equal measured total cost.

**Entry condition:** a justified actionable signal, a supported live observation/control interface, and output-equivalence tests. Any suffix-resampling action additionally requires the relevant M4 gate.

**Planned deliverables:**

- [ ] Implement actual online observation and the supported policy actions: continue, restart, verify, abstain, and validated suffix resampling where available.
- [ ] Measure when generation levels complete and the actual time/work remaining; separate hook, transfer, feature, probe, verifier, and logging costs.
- [ ] Compare against full-depth generation, unconditional retries, verifier best-of-N, fixed-level restarts, and simple confidence/partial-board heuristics.
- [ ] Enforce the same declared wall-clock and/or GPU-work budgets; count abandoned work, retries, monitoring, and verification.
- [ ] Evaluate paired outcomes on the same held-out puzzles: solved rate, cost per correct result, latency distribution, recovery, collateral damage, and sequential false alarms.
- [ ] Publish quality/cost frontiers and cases where probing harms results.

**Gate:** a real online benchmark demonstrates the prespecified benefit over strong equal-budget controls. Offline replay alone does not pass. If interventions add no value, record that result and retain the system as a diagnostic research tool.

**Planned artifacts:** live controller and budget tests, measured policy traces, and `results/reports/live_intervention_benchmark.md`.

## 9. Phase 5 — Generalize to natural-language factual reliability (M6)

**Objective:** determine whether the method transfers beyond exact-verifiable Sudoku.

**Status:** later stretch extension; not required to declare a scoped Sudoku study complete. Its findings must be evaluated independently rather than inferred from Sudoku.

**Planned deliverables:**

- [ ] Reproduce the official WMT14 German-to-English and XSum checkpoint paths with task-specific provenance and baseline equivalence.
- [ ] Define source-grounded error targets: quantities, entities, negation/meaning changes, unsupported claims, and contradictions.
- [ ] Start with controlled exact factual constraints, then create a documented annotation/adjudication protocol.
- [ ] Keep source/document identities and related examples grouped across partitions; prevent reference or evaluator labels from leaking into features.
- [ ] Validate semantic labels independently; if an LLM judge is used, measure agreement with human labels and document evaluator weaknesses.
- [ ] Compare latent probes to partial-text semantic checkers and input-only controls under a frozen task-specific protocol.
- [ ] Report cross-task predictive value and, only if actually tested, cost-matched intervention results.

**Gate:** independently trustworthy semantic labels and held-out evidence support the stated task-specific conclusion. BLEU/ROUGE alone do not establish factual faithfulness. A safety claim requires a separately defined and validated safety target.

**Planned artifacts:** task configurations, annotation guidelines, label-quality audit, task-specific manifests and research reports.

## 10. Phase 6 — Optional research explorer (M7)

**Objective:** make validated research trajectories and conclusions easier to inspect.

**Entry condition:** useful Phase 2 evidence and documented research conclusions, as required by the design. Branch/intervention views require those features to have passed their own gates. The current M3 result does not pass the useful-signal condition.

**Planned deliverables:**

- [ ] Load versioned read-only research artifacts into an optional React viewer.
- [ ] Show input puzzles, all candidate boards, clue/conflict diagnostics, and current versus final correctness.
- [ ] Plot measured risk probabilities with calibration and provenance context.
- [ ] Add alternate-completion and equal-budget policy views only for real validated artifacts.
- [ ] Label measured data, illustrative examples, unavailable values, and superseded runs clearly.
- [ ] Verify layout, accessibility, and responsive behavior; link every conclusion to its report/manifest.

**Gate:** the viewer faithfully represents validated artifacts and limitations. It cannot replace research evidence or turn post-hoc traces into a demonstrated live defense.

**Planned artifacts:** optional explorer, artifact-loading contract, usability checks, and a demonstration linked to the research reports.

## 11. Research release and closeout

The design's release targets are evidence bundles. They do not imply that successful results or later phases are guaranteed.

| Target | Required evidence | Current interpretation |
|---|---|---|
| v0.1 | Loaded checkpoint, official smoke, tested verifier, recorded environment/source | Evidence exists; scoped reproducibility package uses version `0.1.1` |
| v0.2 | Full-level observations, final equivalence, leakage checks, transition analysis | Evidence and agent case review exist; timing limits remain |
| v0.3 | Frozen grouped probes, controls, calibration, held-out metrics and uncertainty | Initial and bounded follow-up evidence exists; useful latent improvement remains unproven |
| v0.4 | Tested frozen-prefix resume and stochastic recoverability | Not reached |
| v0.5 | Real live interventions with strong equal-cost comparisons | Not reached |
| v1.0 research report | Reproducible declared study, provenance, findings, uncertainty, failure analysis and limitations; optional viewer | Scoped negative study and replay package completed; full v1.0 milestone not claimed |

**Closeout tasks:**

- [x] Record the manual case walkthrough, independent label/calibration audit, protected-evidence checks, and bounded follow-up results.
- [x] Declare the current study scope and deferred milestones in the [scoped closeout](results/reports/sudoku_study_closeout.md); do not describe M0–M3 as completion of the entire roadmap.
- [x] Consolidate the initial and follow-up findings, negative results, methods and threats to validity in the linked research reports.
- [x] Verify restoration from a fresh checkout with documented artifact downloads and the recorded environment; distinguish a machine snapshot from a portable dependency lock. See [reproduction evidence](results/reports/clean_checkout_reproduction.md).
- [x] Audit report links, source/data/checkpoint hashes, source snapshots, and reproducible commands; record checked licensing statements and the unselected project license in [notices](THIRD_PARTY_NOTICES.md).
- [ ] Recheck primary literature before any future publication/novelty claim. No such claim is included in this package.
- [x] Tag/package the scoped `0.1.1` reproducibility delivery after its declared replay criteria pass. A v1.0 research milestone, paper submission, or public hosted deployment remains separate work.

A scoped negative-result report is a valid closeout route. It leaves M4–M7 explicitly deferred rather than marking them completed or silently removing them. The current results do not justify a deployment-ready protection system.

## 12. Working rules and next decision

- Work on the selected milestone, satisfy its evidence gate, record remaining gaps, then stop at that boundary. Update this roadmap when scope or status changes.
- Keep final labels and future state outside decision-time features; group and bootstrap by puzzle/source identity.
- Preserve the original baseline, raw evidence, superseded experiments, and negative findings. Never substitute synthetic fixtures for actual model results.
- Reuse compatible, versioned read-only interfaces with Anytime NCM when available. Extract a shared core only after interfaces stabilize; the combined stopping/intervention controller remains outside v1 scope.
- Keep weights, datasets, private data, secrets, and large activation dumps outside normal Git commits. Record necessary artifacts through hashes and manifests.
- Prioritize measured correctness and cost over UI or larger models. No fixed calendar dates or compute estimates are asserted without a scoped experiment plan.

**Current decision:** the bounded M3 follow-up, negative-result closeout, and scoped reproducibility delivery are complete. Stop the current representation search. A new M3 study, an independently motivated M4 recoverability study, or a publication effort requires a separately selected scope and its prerequisites. No later research phase has started, and the full roadmap remains preserved.

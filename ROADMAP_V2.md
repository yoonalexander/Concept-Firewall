# Concept Firewall: improved research roadmap

**Created:** October 24, 2026

**Status:** V2-0 through V2-3 implemented and evaluated. Confidence improved development discrimination, but neither candidate met the practical gate. This bounded study is closed; 1,600 confirmation puzzles remain unused by the model.

**Immediate objective:** determine whether the generation transformer's internal activations and confidence provide a useful early warning of eventual Sudoku errors.

**Project question:** can we catch an answer heading toward a mistake early enough, accurately enough, and cheaply enough to help the model recover?

This is a new study within the existing project. “V2” identifies the research plan; it does not change the released Python package version or declare a v2.0 release. The [original design](Concept_Firewall_Design_Document.md), [original roadmap](ROADMAP.md), and completed study remain intact. The V2 phase numbers below are separate from the original M0–M7 milestones.

## 1. What changes and why

The completed study tested code-derived features, pooled tokenizer representations, and two fixed spatial projections. They did not establish useful incremental prediction under the tested protocols. The [study closeout](results/reports/sudoku_study_closeout.md) and [follow-up report](results/reports/m3_followup_evaluation.md) remain the record of that result.

The next hypothesis concerns different measurements:

| Measurement | Plain meaning | V2 role |
|---|---|---|
| Partial-board diagnostics | What is visibly wrong with the current candidate? | Required cheap control |
| Generator confidence | How concentrated are the model's code-choice scores? | New control and possible cheap detector |
| Generator activations | What information is present inside the transformer while it chooses the next codes? | New candidate source of warning signals |
| Tokenizer/code summaries | What information is retained in the existing reconstruction features? | Historical comparison; their negative result is preserved |

Activations and confidence are hypotheses to test. They are not human-readable thoughts, explanations of intent, or established predictors of mistakes. Confidence in a code choice is not automatically a calibrated probability of final correctness.

**Sequence:** define the experiment → validate measurement → prepare independent data → test a small set of detectors → confirm once → measure live observation cost → consider recovery and intervention only if justified.

## 2. Phase map

| Phase | Question or deliverable | Entry requirement | Status |
|---|---|---|---|
| V2-0 — Study contract | What exactly are we testing, and when do we stop? | New study selected for implementation | Passed; protocol frozen, 94 tests / 123 subtests |
| V2-1 — Correct measurement | Can we observe activations and confidence without changing generation or seeing the future? | Frozen measurement specification and pilot budget | Passed; all 128 paired pilot generations equivalent |
| V2-2 — Data and partitions | Can we obtain a suitable, independent project confirmation set? | Frozen source, sampling, overlap, and partition rules | Passed; 8,000 validated groups with 1,600 confirmation inputs sealed |
| V2-3 — Bounded detector study | Do the new signals add useful prediction over strong controls? | Measurement tests and data boundaries pass | Completed; no candidate passes development criteria |
| V2-4 — Sealed confirmation | Does the frozen result hold on previously unused project puzzles? | One candidate and all decisions frozen | Not started; V2-3 gate failed, inputs/outcomes remain closed |
| V2-5 — Live observation | Is the confirmed warning early and inexpensive in actual generation? | Predictive confirmation passes | Gated |
| V2-6 — Recovery | Can alternative continuations improve outcomes from a fixed prefix? | Useful warning and a separately frozen recovery protocol | Gated |
| V2-7 — Intervention | Does acting on the warning outperform equal-budget alternatives? | Validated recovery/action interface and measured costs | Gated |
| V2-8 — Extension and release | What transfers, and what can we responsibly publish or package? | Scope-specific evidence gates | Conditional; scoped closeout allowed at every phase |

Each phase ends with a report and a recorded **pass, fail, or inconclusive** decision. A completed phase does not imply a successful hypothesis. Inconclusive evidence does not authorize progression as though a gate passed.

## 3. V2-0 — Freeze the study contract

**Deliverables**

- [x] Write a separately named V2 protocol and study identifier; do not edit historical protocols or reuse their run IDs.
- [x] Define final structural correctness using the existing clue-preserving Sudoku verifier. Keep current-board correctness separate from eventual correctness.
- [x] Fix the exact observation boundary, activation location, feature extraction, primary level, controls, model capacity, selection rule, metrics, uncertainty calculation, and stopping rules.
- [x] Define development, validation, threshold-calibration, and sealed-confirmation roles. Record every prior exposure of legacy data.
- [x] Set sample sizes using a prospective power/precision analysis based on legacy development evidence. Freeze the new sample count before outcome inspection.
- [x] Save source/checkpoint/protocol hashes, hardware assumptions, resource accounting, and the decision required to advance.

**Completed evidence:** [V2-0 contract and validation](docs/v2_study_contract.md). The starting choices below are fixed in [the executable protocol](configs/v2_study.json). Source selection was unresolved at contract freeze and subsequently passed in V2-2.

**Starting choices frozen before fitting**

- Same pinned Sudoku checkpoint and upstream source; no larger model or model training.
- Primary observation after hierarchy level 6 completes, before level 7 begins. A level number is not a measurement of elapsed or remaining computation.
- One activation source: the final normalized transformer output feeding the current level's prediction head. Exclude unrelated prefix positions from the primary activation summary.
- One fixed, label-independent position-aware projection to 256 activation features. Freeze its mapping and seed; do not search layers, projection seeds, or feature widths after inspecting results.
- A few declared scalar confidence summaries: normalized code-distribution entropy, top-two probability margin, and selected-code score. Define score normalization across heads explicitly. For deterministic generation, derive summaries from raw logits using a fixed analysis temperature; do not compute entropy from a collapsed temperature-zero sampling distribution.
- Small regularized linear models, with at most two regularization values. No neural probe architecture search in this study.

**Gate:** the protocol and budgets exist before outcome-dependent feature/model selection. Record any change as a new exploratory protocol; never relabel an amended study as the original confirmation.

## 4. V2-1 — Capture the actual generation signals safely

**Deliverables**

- [x] Add an observational wrapper around the pinned upstream generator. Keep the upstream submodule unchanged.
- [x] Capture only the declared current/past activations and logits during the real generation loop. Avoid reconstructing them through a computation that attends to future codes.
- [x] Record when scores and activations become available relative to sampling, partial-board decoding, and completion of the current level.
- [x] Export detached bounded summaries, not unbounded activation dumps. Use independent randomness for any fixed projection so observation does not consume the generator's RNG stream.
- [x] Prove complete code-sequence and final-board equivalence between observed and unobserved runs under identical inputs, seeds, settings, and batches.
- [x] Test that future codes, reference solutions, final labels, and later hooks cannot change an earlier observation. Disallow fitting transforms on assessment data.
- [x] Test hook cleanup, repeated calls, batch identity/order, finite features, device transfer, and memory bounds.
- [x] Run a small operational pilot on at most 128 declared legacy development puzzles. Count all instrumented/control generation work against the budget.

**Completed evidence:** [V2-1 measurement validation](results/reports/v2_measurement_validation.md), with 99 passing tests / 123 subtests and exact paired equivalence on all 128 pilot puzzles. No detector performance claim follows from this gate.

**Gate:** exact generation equivalence, decision-time boundaries, and bounded capture pass. Failed equivalence is an engineering failure to fix before interpreting detector scores.

**Planned outputs:** observation schema, source-pinned capture manifest, invariance/leakage tests, and a measurement validation report.

## 5. V2-2 — Establish independent project data

**Deliverables**

- [x] Inventory candidate fresh Sudoku sources or a documented puzzle-generation procedure; record licensing, provenance, difficulty criteria, and exact validation.
- [x] Validate puzzle clues and solutions independently. Predeclare whether uniqueness is required, and verify it where required.
- [x] Check exact overlap and relevant Sudoku equivalences against legacy data and across new partitions. Group related puzzles together; document the canonicalization method and any unverified equivalences.
- [x] Freeze sampling and inclusion rules without selecting puzzles for favorable detector outcomes. Preserve natural failure prevalence and record malformed/failed runs.
- [x] Allocate new training/development, validation, threshold-calibration, and confirmation groups before inspecting final outcomes. Keep confirmation inputs and labels outside all selection and fitting paths.
- [x] Check available checkpoint-training provenance. Fresh to this project does not establish absence from checkpoint training; disclose unknown exposure.
- [x] Freeze the sample count and a minimum useful failure-count/precision rule. If realized confirmation evidence is too sparse, report inconclusive; do not keep adding samples until a desired result appears.

**Completed evidence:** [V2-2 data validation](results/reports/v2_data_validation.md). Conservative invariant grouping covers standard Sudoku symmetries without claiming a full canonical form. New-source distribution and unknown checkpoint-training exposure remain explicit limitations.

All original 2,000 puzzles are now legacy/exposed evidence for study design. Any V2 development reuse must be declared explicitly without rewriting their historical split membership. They cannot supply V2's fresh confirmation claim. Digit permutations, transposes, or repartitioning the same puzzles do not make them independent confirmation data.

**Gate:** a suitable source and frozen partitions are documented before fitting. If fresh data cannot be obtained within budget, only a clearly labeled development feasibility study may proceed; V2-4 and later phases stay closed.

**Outputs:** [source review](results/v2/contracts/v2-source-review.json), [immutable data/partition manifest](results/v2/contracts/generator-signals-v1-data.json), validation report, and the V2-0 sample-size rationale. The planned count is now realized; no new-source model result is established yet.

## 6. V2-3 — Run one bounded detector comparison

**Question:** does the declared activation representation add useful warning information beyond what is already visible in the input, partial board, and generator confidence?

**Required comparisons**

| Model family | Purpose |
|---|---|
| Partial-board diagnostics | Cheap observable baseline |
| Input + partial-board diagnostics | Control for input difficulty |
| Partial-board diagnostics + confidence | Test whether confidence alone supplies the useful new signal |
| Input + partial-board diagnostics + confidence | Stronger combined cheap control |
| Selected cheap control + declared activation features | Primary test of incremental activation information |

**Deliverables**

- [x] Apply identical puzzle-group boundaries and fitting rules to controls and the activation candidate.
- [x] Fit scaling and all learned transforms on training data only. Select hyperparameters on development/validation data only; set operating thresholds on a separate calibration partition. Declared final refits use training+validation only.
- [x] Freeze a cheap-control selection rule aligned with the primary detection objective. Report every required control; do not claim superiority by comparing only against a weak selected control.
- [x] Use raw score ordering for primary discrimination. Specify any calibration separately; prohibit outcome-driven sign flips or recalibration on confirmation outcomes.
- [x] Report AUROC, precision-recall performance, recall at the declared false-alarm operating point, observed false-alarm rate, failure prevalence, and paired uncertainty.
- [x] Record training-versus-assessment gaps and label-shuffled diagnostics. Keep optional descriptive checks within the frozen run budget.
- [x] Apply the at-most-one-candidate rule: neither qualifies, so no candidate is frozen and confirmation stays closed.

**Completed evidence:** [V2-3 results, audits, and scoped closeout](results/reports/v2_detector_study.md). Confidence catches 22.52% of calibration mistakes at 4.89% false alarms; the target is 40%. Activations catch 19.07% and do not improve on the confidence control. All 16 fits are consumed. These are development results, not confirmed unseen-population performance.

Confidence alone may win. That would support a cheaper confidence-based monitor, not a claim that activations add information. The protocol must declare this possible fallback in advance, including its comparator and confirmation rule; it must not silently create a second post-hoc hypothesis.

**Gate:** the predeclared development criteria pass without broadening the search. Otherwise, write the negative/inconclusive report and close this study. A promising development score alone is not a result on unseen confirmation puzzles.

## 7. V2-4 — Evaluate the frozen detector once

**Deliverables**

- [ ] Score the sealed confirmation groups once with the frozen candidate and controls.
- [ ] Use the previously fixed threshold; report actual false alarms instead of retuning to obtain a flattering operating point.
- [ ] Compute paired puzzle/group uncertainty using the frozen method. State which fitting/selection uncertainty the intervals do and do not cover.
- [ ] Retain all evaluated puzzles and failures, including inconvenient cases. Publish negative and inconclusive outcomes alongside successful checks.
- [ ] Record a decision for predictive usefulness, distinct from online cost, recovery, or production safety.

**Practical targets frozen in V2-0; not met in V2-3**

| Measure at the primary early observation | Proposed target |
|---|---|
| Share of eventual mistakes detected | At least 40% recall |
| False alarms among eventually correct answers | At most 5% observed, with a one-sided 95% upper bound no greater than 8% |
| Recall improvement over the required cheap comparator | At least 10 percentage points, with a positive lower bound on the paired 95% interval |
| Additional metrics | Report AUROC, precision-recall, calibration where applicable, and uncertainty; do not substitute a secondary metric for a failed primary target |

These targets were frozen in V2-0 with the prospective rationale. They are not achieved results and cannot be lowered after the V2-3 outcome. A chosen candidate would have to satisfy its declared comparator rule; a confidence-only winner could not establish incremental activation value.

**Gate:** the fixed confirmation criteria pass with sufficient precision. A failure closes the current detector hypothesis. Further representation searches require a new question, protocol, and independent confirmation plan.

## 8. V2-5 — Measure a live observer's cost and warning time

**Deliverables**

- [ ] Run the confirmed monitor inside actual generation in observation-only mode; it must not yet change sampling or choose actions.
- [ ] Measure paired baseline/observed runs with warmup and appropriate synchronization. Include hooks, transfers, summaries, partial decoding, probe inference, and required logging.
- [ ] Measure actual time/work remaining when an alert becomes available. Do not infer available savings from hierarchy level or offline replay time.
- [ ] Report end-to-end latency distribution, memory, failure detection, and false alarms under the real observation path.
- [ ] Test a proposed monitoring-overhead ceiling of 5% of baseline end-to-end generation latency, using the aggregate/statistical rule frozen in the timing protocol. Retain tails and uncertainty.

**Gate:** predictive usefulness survives real observation, warnings arrive before useful remaining work is exhausted, and the measured cost ceiling passes. If prediction works but monitoring is too expensive or late, retain the diagnostic finding and stop the intervention path.

## 9. V2-6 — Test recovery from a frozen prefix

This phase starts only after the useful-warning and observation gates pass and a recovery protocol is selected. No resume/branching implementation is implied by the earlier phases.

**Deliverables**

- [ ] Define the complete resume state: immutable code prefix, relevant caches, sampling configuration, and RNG state.
- [ ] Verify uninterrupted/resumed equivalence under identical settings and prove earlier codes cannot change.
- [ ] Predeclare a genuinely stochastic suffix policy, branch count, seeds, prefix-selection rules, and total generation budget.
- [ ] Measure recovery from the same fixed prefixes, counting unsuccessful branches and total cost. Report all selected prefixes, not only favorable cases.
- [ ] Compare high-risk and matched low-risk prefixes and simple selection heuristics to assess whether the detector identifies useful recovery opportunities.

**Gate:** resumption is valid, branches are reproducible, and evidence supports the prespecified recoverability criterion. The deterministic published continuation repeated several times is not a recovery distribution. Recoverability alone does not establish a useful live policy.

## 10. V2-7 — Test whether intervention is worth its cost

**Deliverables**

- [ ] Freeze one simple policy and the actions it may take; tune it without accessing its final assessment outcomes.
- [ ] Compare against ordinary full-depth generation, unconditional retries, fixed-level restarts, verifier best-of-N, and relevant cheap confidence/board heuristics.
- [ ] Enforce the same measured total wall-clock or GPU-work budget across policies. Count monitoring, decoding, aborted generation, retries, verification, and failed attempts.
- [ ] Evaluate paired outcomes on suitably independent assessment puzzles: solve rate, cost per correct result, latency, recovery, and harm from unnecessary intervention.
- [ ] Require a prespecified practical correctness gain with uncertainty at equal cost. New policy tuning must not repeatedly reuse V2-4 confirmation as a fresh final test.

**Gate:** live intervention beats the strongest required equal-budget comparator under the frozen practical criterion. If it does not, report a useful detector or recoverability result without claiming prevention or efficiency benefits.

## 11. V2-8 — Conditional extension and scoped release

**Natural-language extension, if selected**

- [ ] Choose one task and a narrow source-grounded error definition, such as changed quantities or unsupported entities.
- [ ] Reproduce that task's checkpoint/baseline and create task-specific data boundaries, labels, controls, and independent annotation checks.
- [ ] Repeat prediction, cost, and intervention gates for that task. Sudoku performance does not establish factuality, harmful-content detection, or privacy protection.

**Packaging and reporting, valid for positive, negative, or inconclusive outcomes**

- [ ] Consolidate the question, frozen methods, all attempts, metrics, uncertainty, costs, case studies, and limitations.
- [ ] Preserve original and V2 evidence in separate namespaces. Keep large data/activation/model artifacts outside ordinary Git history, with checksummed inventories and restore instructions.
- [ ] Verify a clean checkout/environment and exact claims supported by reproducible artifacts.
- [ ] Review licensing and primary literature before any publication or novelty claim; select release version/tag only for the scope actually delivered.
- [ ] Consider a small read-only viewer only if it helps interpret actual retained evidence. No frontend is needed to establish the scientific result.

A scoped closeout may occur after any failed gate. It does not mark conditional phases complete or erase them from the roadmap.

## 12. Frozen budget for the initial V2 detector study

These resource ceilings were frozen in V2-0 and apply collectively through V2-5. They are not runtime estimates. Recovery, intervention, and task transfer would each require a separately declared budget. Remaining GPU capacity does not authorize further model searches after a failed gate.

| Resource | Proposed limit or rule |
|---|---|
| Paid compute/services | None |
| Hardware | Existing local GPU; one CPU fitting thread; no subagents |
| Checkpoints/upstream | Existing pinned model and unmodified source |
| Operational pilot | At most 128 declared legacy development puzzles |
| New puzzle population | At most 8,000 unique puzzles; exact count and partition sizes fixed prospectively |
| GPU execution | At most 60 cumulative measured minutes across pilot, capture, checks, failed attempts, and timing runs; also record elapsed wall time |
| Probe fitting | At most 16 declared final fitting/calibration jobs and 15 minutes CPU fitting time; account for every inner-fold/refit job explicitly before choosing a selection procedure |
| Activation representation search | One declared layer/location, projection, seed, and width; no post-result expansion |
| Retained feature storage | At most 2 GiB; bounded summaries only |
| Confirmation | One frozen candidate and one outcome evaluation; no confirmation-driven tuning |

Check feasibility before committing to sample sizes and model selection. If the precision requirement cannot fit within these caps, reduce the claim or stop for a newly selected scope; do not silently increase the budget. Budget exhaustion produces an incomplete/inconclusive record, not an artificial success declaration.

## 13. Immediate next deliverable

**Current study closed at V2-3.** The [report](results/reports/v2_detector_study.md) preserves the confidence finding, practical failure, resource accounting, and reproduction limits. Keep the 1,600 confirmation inputs/outcomes outside further model work under this study.

Commit and push after each completed phase, as requested. V2-4 through V2-7 are not started; task transfer, viewer, and formal release remain conditional. No confirmed useful detector, recovery benefit, or live compute saving is established. Further research requires a newly selected study rather than changing this one's frozen criteria.

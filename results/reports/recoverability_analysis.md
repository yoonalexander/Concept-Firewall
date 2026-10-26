# Can saved decision-time features predict recovery?

**Decision: inconclusive evidence; no-go for advancing the learned allocator to an independent study under the frozen triage rule.** The primary combined logistic model fails the rule for both actions. This does not reject recoverability prediction in general. A cheap low-entropy ranking is a secondary hypothesis, not confirmed benefit.

At 272 retries, the primary model recovers 20 fixed-prefix failures versus 16.97 expected under verifier-first random allocation, and 30 full-restart failures versus 28.28 expected. Both two-action 97.5% conditional intervals include no gain. Monitoring nearly erases the prefix gain and reverses the restart gain. The cheap low-entropy control recovers 24 and 38, exceeding the learned model in both cases.

## Scope and frozen protocol

The [protocol](../../docs/recoverability_analysis_protocol.md) and [executable specification](../../configs/recoverability_analysis.json) were committed and pushed as `0046a38` before fitting; the evaluator and synthetic tests followed as `f58300e`, also before fitting. Source main was `a5ea81eb1e3e6085473b69cb7944a571bdee8794`. A separate `codex/recoverability-analysis` worktree/branch contains this work. Original consumed ledgers and failed gates were read only. Their hashes are in the [inventory](../recoverability/inventory.json).

Only the already exposed recovery cohort has paired potential retry outcomes: 1,600 distinct puzzle groups, 590 original successes retained, 1,010 original failures eligible for allocation. There are 63 potential prefix rescues (6.24% of failures) and 105 potential restart rescues (10.40%). Other exposed cohorts lack action-specific retry labels and cannot expand this supervised sample without new generation. No new generator outputs were made.

Each target means that the one saved identity-seeded retry at temperature 0.5 verifies valid, conditional on original failure. Targets are action specific: fixed level-6 prefix with sampled suffix versus full stochastic restart. They are potential outcomes of those particular procedures, not intrinsic recoverability, probability across seeds, effect of repeated retries, or a general safety label. Independent and production exact Sudoku verifiers agreed on every original and retry outcome.

## Features and evaluation

Predictors contain only information available at the level-6 decision boundary: eight sorted current-board diagnostics, six generator confidence summaries, five input clue-count summaries, and prefix entropy/unique fraction (21 combined features). The eight decoded values were reconstructed from the saved current board at the prefix boundary; the six confidence summaries were reused from the historical online observer record. Saved logits are unavailable, so those six summaries cannot be independently recomputed here. The frozen failure score was replayed. Current-board diagnostics are allowed; final-board diagnostics are excluded. Future codes, final boards, retry seeds/latencies/boards/codes/outcomes, source rating, identities and reference solutions are excluded from predictors. Original verification supplies eligibility only. A strict `Decision` dataclass isolates extraction from outcome-bearing rows.

Five folds are assigned by sorting symmetry-group hashes and round robin, without outcome stratification. All related records and both action labels for a group share a fold. Each model trains only on the other folds of original failures. StandardScaler learns means/scales on training rows only. There is no tuning, threshold search, repeated cross-validation, winner refit, or final all-data fit. Exact retry totals are allocated proportionally across held-out folds using largest-remainder quotas; ranking stays within folds to avoid comparing differently fitted probability scales. Stable identity hashes break ties. Fold quotas describe an offline evaluation policy, not an evaluated streaming controller.

The four fixed specifications per action are: input-only logistic; decoded/confidence logistic; primary combined logistic; secondary combined histogram boosting. Logistic uses C=0.1, lbfgs, max_iter=1000 and no class weighting. Histogram boosting uses 100 iterations, seven leaves, min_samples_leaf=30, L2=10, 32 bins, learning rate 0.1 and no early stopping. There are five fits for each specification/action, totaling 40, with one CPU thread. All settings were frozen before recovery fitting.

## Matched retry counts

Entries are verified rescues at **68 / 136 / 272** retries, selected among original failures. Uniform expectations are exact over globally uniform fixed-size failure subsets. Ranked controls and OOF models use the same fold quotas. Hash random is one frozen realization, not an optimized seed; its unusually poor prefix draw illustrates why the expectation is the primary comparator.

| Policy | Fixed-prefix rescues | Restart rescues |
|---|---:|---:|
| Verifier-first uniform expectation | 4.24 / 8.48 / 16.97 | 7.07 / 14.14 / 28.28 |
| Verifier-first frozen hash | 2 / 3 / 9 | 11 / 18 / 34 |
| Existing failure score, high first | 2 / 4 / 9 | 7 / 15 / 23 |
| Existing failure score, low first | 8 / 15 / 23 | 10 / 18 / 34 |
| More input clues first | 2 / 8 / 13 | 5 / 14 / 30 |
| Fewer current conflicts first | 4 / 6 / 9 | 11 / 19 / 31 |
| Lower level-6 entropy first | 12 / 17 / 24 | 12 / 18 / 38 |
| Input-only logistic | 2 / 6 / 13 | 10 / 15 / 24 |
| Decoded/confidence logistic | 4 / 10 / 22 | 6 / 17 / 30 |
| PRIMARY combined logistic | 5 / 10 / 20 | 11 / 14 / 30 |
| Combined histogram boosting | 4 / 9 / 20 | 4 / 11 / 23 |

The original confidence-alert policy is different: it spent 272 retries including 30 original successes, and recovered **9 / 21**, exactly reproducing the historical result. The ranked failure-score control above spends all 272 slots on verified failures, recovering **9 / 23**. Neither result changes the historical failed gate.

| Primary model, 272 retries | Fixed prefix | Full restart |
|---|---:|---:|
| Recovery AUROC | 0.566 | 0.499 |
| Recovery average precision | 0.076 | 0.112 |
| Uniform AP reference / prevalence | 0.062 | 0.104 |
| Extra rescues vs uniform expectation | +3.03 | +1.72 |
| 97.5% interval, extra rescues | [-4.73, +11.30] | [-8.01, +11.81] |
| Accuracy gain on 1,600 originals | +0.189 pp | +0.108 pp |

The primary model improves on descending failure risk, but does not beat lower entropy. Paired primary-minus-entropy differences are **-4 rescues, 95% [-12, +3]**, and **-8, [-19, +3]**. Primary-minus-descending-risk differences are **+11 [1, 22]** and **+7 [-6, 20]**. These are exploratory conditional comparisons, not evidence of superiority to verifier-first random allocation.

Lower entropy has AUROC **0.627 / 0.553** and average precision **0.124 / 0.140**. Its count gains are **+7.03 / +9.72** rescues. The respective 95% intervals are **[-0.22, +14.74] / [+0.70, +19.06]**; the two-action 97.5% intervals are **[-1.12, +15.68] / [-0.39, +20.44]**. The restart nominal 95% result is a hint among multiple disclosed comparisons. It does not survive the two-action interval, and the cost-matched interval below includes no gain. Secondary findings do not replace the frozen primary.

## Monitoring and uncertainty

The historical 20 paired synchronized local timing trials give 137.80 ms plain service and 147.39 ms monitored service: 9.59 ms (6.96%) monitoring overhead. The timing-pair bootstrap interval here is [5.86, 13.26] ms. Every feature-based policy conservatively pays full monitoring on all 1,600 puzzles. Input-only/hash policies pay plain service. This can overcharge confidence-only controls, but a lower-cost implementation has not been measured.

The shared replay envelope is 1,600 times mean monitored service plus 272 times the maximum observed retry latency (336.04 ms prefix; 263.56 ms restart). It is **327.23 / 307.52 seconds**. Baselines avoid monitoring and receive **317 / 330** retry slots. Maxima are observed, not guaranteed latency bounds; this is additive sequential replay accounting, not a production latency experiment.

| Policy at the common envelope | Prefix rescues | Restart rescues |
|---|---:|---:|
| Verifier-first uniform expectation (317 / 330 retries) | 19.77 | 34.31 |
| Verifier-first frozen hash (317 / 330 retries) | 12 | 43 |
| Primary combined logistic (272 retries) | 20 | 30 |
| Lower entropy (272 retries) | 24 | 38 |

Primary cost-matched gains are **+0.23, 95% [-6.67, +7.30]** and **-4.31, [-13.00, +4.42]** rescues. Low entropy gains are **+4.23, [-2.95, +11.79]** and **+3.69, [-5.28, +12.73]**. Timing uncertainty alone puts the primary prefix gain between **-0.90 and +1.35** rescues. New scorer latency was not measured; no live controller or actual speedup is claimed. The primary prefix point gain disappears at roughly **0.76 additional ms per original puzzle** of unaccounted scoring overhead. This is an approximate break-even sensitivity, not a benchmark.

All outcome intervals use 10,000 paired group percentile resamples of fixed OOF predictions and allocation masks. Counts and uniform expectations are recomputed in each draw; timing-pair sensitivity is reported separately. Primary comparisons use 97.5% intervals for the two actions. Other 95% intervals are descriptive, with no simultaneous correction across secondary models, controls or budgets. They omit refitting and ranking/selection instability, checkpoint uncertainty, unknown training exposure, seed-to-seed retry variation and population drift. They are not full confidence intervals for a newly trained deployment policy. A uniform random 272-slot allocation itself has conditional 95% rescue ranges **11-24 / 20-37**, reflecting allocation randomness on this fixed table.

## Decision and future-data requirements

The predeclared triage rule required the primary model to add at least eight rescues (0.5 percentage point on 1,600 originals), have a positive two-action interval, retain a positive service-cost gain and beat the cheap/failure-risk controls. Neither action passes. Upper primary intervals still permit an eight-rescue gain, so the scientific finding is **inconclusive**, with an operational **no-go for advancing this learned allocator**. Rejecting every possible recoverability feature or algorithm would exceed the evidence. Some saved confidence features may contain weak recovery information, particularly for fixed-prefix continuation, but useful allocation advantage is unestablished.

No new confirmation experiment is recommended from these results. If a later, separately authorized study pursues the entropy hint, freeze it as a distinct cheap hypothesis rather than promoting a selected fitted model: one checkpoint, one action (full restart), one low-entropy ranking, one retry budget, and no tuning. Treat this entire cohort as development. Register the service-aware superiority margin (at least 0.5pp accuracy over verifier-first random), cost accounting, uncertainty method and stopping rule before collecting labels. If any fitted policy is used instead, collect separate new training/calibration groups and lock the model before confirmation.

Fresh confirmation requires a disjoint, prospectively sampled and symmetry-group-deduplicated puzzle pool, checked against all 8,000 project groups; project novelty still cannot establish checkpoint training novelty. Collect decision-time features before future generation, independently verify originals and retries, and retain one prespecified identity-seeded potential retry per action for unbiased replay or randomize actual equal-cost allocation prospectively. Use disjoint seeds and prespecified multiple seeds only if that is the target estimand; do not search seeds. Benchmark the actual scorer and monitoring implementation on separate inputs/hardware before fixing the service envelope. Preserve successes and accept retries only after independent verification.

Fresh sample size must be chosen before outcomes using paired-policy variance and the desired service-aware margin, including expected failure prevalence and rare recovery events. This table has only 63 / 105 rescue positives; another 1,600-puzzle run is not justified as adequately powered. As an illustration only, primary-vs-uniform fixed-policy bootstrap standard errors here are roughly 3.6 / 4.4 rescues (0.225 / 0.275pp per 1,600). If true lift were 1.0pp and the required lower-bound margin 0.5pp, a normal approximation with 80% power and a two-sided 97.5% interval gives about 3,100 / 4,600 confirmation puzzles before additional fitting/seed uncertainty. These planning assumptions are optimistic, not a selected sample-size authorization. Observed cost-aware lifts are below the required 0.5pp, so sample size alone cannot make the current policy satisfy the practical target.

## Resources, audit and reproduction

Limits were 40 attempted fits, 600 CPU seconds and 1,200 wall seconds, one thread. The durable [analysis ledger](../recoverability/ledger.json) records **40/40 completed fits**, **7.58 CPU seconds**, **8.39 wall seconds** for the analysis body. The independent no-fit audit used **0.92 CPU seconds / 0.97 wall seconds**, for **8.50 analysis-plus-audit CPU seconds**. Interpreter/import startup, synthetic test execution and report assembly are outside those timed analysis-body figures; they use no research fits. No failed research fits, GPU work, new generator outputs, paid compute, checkpoint searches, subagents or new confirmation cohorts were used.

**15 tests and 3 subtests passed** across the new synthetic tests and existing leakage/grouping tests. They check strict future/outcome exclusion, group disjointness, training-only scaler means, allocation quotas/ties, cluster resampling, service accounting and resource/attempt guards. The [independent audit](../recoverability/audit.json) rechecks labels, all 60 policy/budget point estimates, source hashes and training-only means without refitting. The original 9 / 21 confidence rescues are reproduced.

[Full metrics](../recoverability/results.json), [OOF predictions](../recoverability/oof_predictions.jsonl), [execution hashes](../recoverability/replay_manifest.json), and [reproduction instructions](../../docs/reproduce_recoverability_analysis.md) retain the evidence. The scientific runner refuses a repeated attempt when its separate ledger exists. Existing consumed ledgers remain unchanged. Main remains at the requested starting revision; this branch proposes exploratory analysis and does not authorize future data collection.

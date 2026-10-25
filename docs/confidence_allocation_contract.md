# Confidence allocation: separately registered follow-on

The user authorized implementing the saved-results recommendation and its justified successors, with a commit/push after each step. This contract authorizes one new, narrower study, `confidence-allocation-v1`. The original `generator-signals-v1` stays closed with its 40% recall gate failed. Lower alert coverage is an explicit limitation, not a repaired original result.

## Why this question

[Step 1](../results/reports/confidence_value_check.md) found a hypothetical 4.17 percentage point perfect-recovery allocation advantage over randomly spending the same number of retries across all puzzles. That warrants a bounded feasibility check, not a product claim. Exact final Sudoku verification can identify every incorrect answer, so verifier-first allocation is a required, stronger comparator. Conditional recoverability may differ from failure risk; it must be measured.

## Fixed assets and confirmation question

Freeze the already saved board+confidence logistic model (including its scaler, coefficients, orientation and threshold) byte-for-byte. No refits, recalibration, feature changes, sign changes or temperature search. The confirmation cohort is the existing 1,600 project-held-out groups; their inputs were curated for V2, but model outcomes have never been generated. Checkpoint training exposure remains unknown. After this run, this set is consumed, regardless of the outcome.

The executable criteria in [the protocol](../configs/confidence_allocation.json) require at least 200 puzzles per outcome class, at most 20% alerted, a one-sided 95% Wilson false-alarm upper bound at most 8%, and an allocation-capacity advantage of at least 2 percentage points over random-all with a positive one-sided 95% puzzle bootstrap lower endpoint. The capacity statistic is TP/N minus alert fraction times failure prevalence. With hypothetical uniform 25% recovery, a 2-point capacity advantage yields only a 0.5-point correctness advantage. This screen does not establish that recovery probability, actual value or the old 40% recall target. The primary uncertainty is the prespecified bootstrap; the exact conditional enrichment p-value is descriptive.

## Actual recovery and alternatives

On passing confirmation, run exactly one fixed stochastic suffix attempt per puzzle after a frozen level-6 prefix, at temperature 0.5, top-k 0, top-p 1. Set identity-specific RNG seeds from the fixed study/policy/puzzle/seed hash. Recompute prefix attention using the official generation loop while forcing the first six selected code chunks. Do not call this cached prefix resumption or claim saved prefix compute. Verify deterministic forced-prefix equivalence on the first 32 confirmation rows before stochastic recovery; use tiny-model tests before opening confirmation.

If the primary cannot establish the actual improvement gate, the sole alternative is one full stochastic restart per puzzle using the same temperature. The two-sided 97.5% paired puzzle bootstrap intervals account for the two prespecified recovery-policy comparisons by Bonferroni. No further prefixes, temperatures, seeds or attempts are searched.

Generate a complete paired table of potential retry outcomes; select allocations without using those outcomes. M is the number of fixed confidence alerts. Compare confidence-selected M retries to random-all M retries and verifier-first M retries on verified failures. Use both the exact conditional expected results across uniform subsets and one fixed hash-selected realized baseline. Keep an original valid answer; accept a retry only after independent exact validation. This avoids sacrificing already correct solutions. Record all experimental GPU calls even though the per-policy cost is only its selected calls.

The actual gate requires at least 0.5 percentage point gain versus both random-all and verifier-first at matched counts, with both lower interval endpoints positive. It additionally requires positive realized gain against both under a common conservative service-time envelope. Measure full generator/final decoding and the monitor's actual in-generation prefix decoding/CPU scoring after warmup, alternating order for 20 paired measurements at batch size 1. Hardware-specific timing uncertainty is reported. Base service demand is N times the relevant mean solve time; each retry slot reserves the maximum observed single-puzzle retry time. Baselines may buy extra slots with the monitoring cost they avoid. This is a replay estimate with a conservative measured envelope, not a production latency guarantee or an actual deployment.

## Resource and failure rules

Separate single-writer persistent ledger: 1,200 GPU-assisted elapsed seconds, 8,000 puzzle generation calls, zero fits, 200 MiB retained data. Preserve the old V2 ledger without changes. Local existing hardware only, no paid compute or agents. Timed operations and failed attempts count; an active crashed operation blocks continuation. Only one confirmation attempt and one attempt of each declared recovery policy are allowed.

If confirmation fails or is incomplete, do not claim confirmation or rerun it. The authorized alternative is a bounded exploratory recovery feasibility check on previously exposed development data, with an explicit exploratory label, followed by closeout. A scientific negative result is not a technical blockage to work around by changing criteria. Complete diagnostics, evidence packaging/restoration checks and documentation, then stop when the scoped work is exhausted.

Commands: `.venv\Scripts\python.exe scripts/confidence_allocation.py freeze`, then commit/push the frozen contract before `.venv\Scripts\python.exe scripts/confidence_allocation.py confirm`. Save the original parent manifest, protocol, data and model digests in `results/continuation/frozen.json`; execution refuses changed artifacts and repeated attempts.

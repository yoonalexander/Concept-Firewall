# V2-0: frozen generator-signal study contract

**Decision:** pass for study definition and resource accounting. No detector performance or fresh-data availability is established.

The executable protocol is [configs/v2_study.json](../configs/v2_study.json), study `generator-signals-v1`, SHA-256 `d7a98159ab20b1f92d1d019d8f3d7009afae2107b06953e76639e53b7f2e0cf3`. The [contract](../results/v2/contracts/generator-signals-v1.json) freezes that digest, the historical partition digest, the exact pilot identities, and the four official artifact digests. The [execution manifest](../results/manifests/20261025T024505980857Z-v2-contract.json) retains the full protocol, source snapshot, environment, and prospective calculation. Its date is UTC; the local study date is October 24, 2026.

## Frozen measurement and comparison

Observe one point: level 6 of the pinned deterministic hard-Sudoku generator. Capture the normalized transformer representation entering that level's prediction head and six confidence summaries derived from logits at analysis temperature 1. The score tensors exist before current-code sampling; export immutable summaries associated with the completed current prefix before any next-level computation. Never use later codes or reference solutions as features.

One fixed position-aware Rademacher projection supplies 256 activation features. Its seed, layer, width, and level cannot be searched. Pilot batch size is 8. Generation settings remain unchanged; equivalence with the unobserved generator is the next phase's gate.

Four cheap controls cover board diagnostics, input difficulty, confidence, and their declared combinations. Each receives two regularization choices. Validation is split deterministically into a threshold-selection half and an assessment half; ranking prioritizes the declared false-alarm condition and recall. The activation candidate augments the best confidence-containing control. All controls are reported and are required comparators for an activation claim.

The fit allowance is exact: eight cheap-selection fits, two activation-selection fits, five final refits, and one label-shuffled diagnostic, totaling 16. No calibrator or bootstrap refits are allowed. Calibration data determine thresholds only. An activation candidate has priority if its development gate passes; otherwise a predeclared confidence-only branch may qualify against both non-confidence controls. At most one candidate is confirmed. A failed confirmation cannot switch to the other branch.

## Data and prospective sensitivity

The planned new population is fixed at 8,000 puzzles: 4,000 training, 1,600 validation, 800 calibration, and 1,600 sealed confirmation. Source eligibility and an overlap/provenance audit are required before using any new puzzles. No eligible source is currently declared. If that gate cannot pass, only the original 1,000/300/300 training/validation/calibration partitions may support exposed development feasibility; the old 400 test identities remain excluded from new fitting/capture.

Planning at the historical 13.75% failure rate gives approximately 220 confirmation failures. The frozen minimum is 150 failures and 1,000 successes. In 10,000 simulations, a hypothetical candidate/control recall of 0.40/0.25 with joint true-positive probability 0.15 passed the paired lift/count approximation in 90.46% of draws. This excludes the absolute recall gate and fitting/selection/threshold uncertainty and is **not joint study power or evidence about the candidate model**.

False-alarm sensitivity is reported honestly: a hypothetical true FPR of 3% passed the false-alarm conditions in all simulated draws, while a true FPR exactly at the 5% ceiling passed in 51.07%. An expected boundary value is not a high-probability guarantee. Sparse actual evidence yields inconclusive status, without outcome-driven sample extension.

The final practical criteria remain recall >=40%, observed FPR <=5% with a one-sided 95% Wilson upper bound <=8%, and recall lift >=10 percentage points over every required comparator, with each paired 95% lower endpoint positive. The protocol specifies a conditional paired-group bootstrap, not a model-refitting bootstrap. Confidence-only success is distinct from incremental activation value.

## Resource accounting

The persistent runtime ledger is ignored by Git at `results/v2/runtime/generator-signals-v1.json`. It is bound to the frozen protocol, uses an exclusive writer lock, charges jobs before they run, and records elapsed time and failures. An active operation surviving a crash blocks new work; the allowance cannot silently reset. Preserve or conservatively resolve its record before any continuation.

GPU-assisted synchronized stage elapsed time conservatively includes loading/host work; it is a budget charge, not a kernel-speed measurement. Checks run between bounded batches/jobs. One indivisible operation may overshoot a remaining time allowance; that overshoot is retained and prohibits further work. This is not a hard real-time cancellation guarantee.

Caps: 3,600 GPU-assisted seconds, 900 CPU fitting seconds, 16 fits, 128 pilot identities, 8,000 new identities, and 2 GiB features. Failed attempts count. Existing local hardware only; no paid compute, new checkpoint, or subagents. Later recovery/intervention budgets remain unselected.

## Validation and next phase

The verification run passed **94 tests and 123 subtests** and `pip check`. Added checks exercise protocol/fit-budget consistency, prospective sensitivity, amended-contract rejection, persistent failed-fit charging, time overshoot, interrupted-operation rejection, and invalid charges. Early test failures exposed a Windows lock-file cleanup issue and an overly exact floating-point assertion; both were fixed before freezing the contract. No model generation or probe fitting ran in V2-0.

Reproduce the contract check with `.venv\Scripts\python.exe -m concept_firewall v2-contract`. Existing frozen contracts are validated rather than overwritten. V2-1 is authorized by the user's roadmap implementation request and now eligible: build and test the observation path, then commit/push that phase before progressing.

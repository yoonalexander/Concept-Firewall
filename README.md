# Concept Firewall

Research tools for asking whether a frozen Next-Concept Modeling hierarchy predicts eventual Sudoku errors. This is an experiment in structural correctness, not a production safety system.

The supplied [design](Concept_Firewall_Design_Document.md) remains canonical. The [review](docs/design_review.md) identifies scientific limitations and implementation decisions. Only recorded runs establish a release gate; unit-test fixtures are not model results.

See [ROADMAP.md](ROADMAP.md) for every project phase, the M0–M7 milestone mapping, current status, deliverables, and evidence gates.

The released evaluator has now run on all 2,000 hard-Sudoku puzzles: **1,725 solved (86.25%)**. Corrected full-prefix collection produced **24,000 records**, with every final output matching the official baseline. See [baseline evidence](results/reports/baseline_reproduction.md) and [trajectory analysis](results/reports/level_trajectory_analysis.md). A reconstruction error found during review is documented transparently; initial native-length reports are superseded.

**Initial M0–M3 result:** the prespecified level-6 pooled-latent increment is **−0.0078 AUROC (95% interval −0.0368 to +0.0193)**, so useful incremental prediction was not demonstrated. See [probe evaluation](results/reports/probe_evaluation.md). The initial verification passed **74 tests and 119 subtests**; saved probes reproduce all 400 held-out predictions for each of five audited primary-level families. Later phases remain gated.

**October 23 follow-up:** independent label checking and agent case review passed. Two fixed spatial variants were tested on **1,600 development puzzles**, excluding all 400 original test puzzles. Neither met the primary continuation criteria. The bounded Sudoku study is [closed with a negative report](results/reports/sudoku_study_closeout.md); see [audit and follow-up results](results/reports/m3_followup_evaluation.md). Current verification passes **87 tests and 119 subtests**. This is not fresh confirmatory evidence or completion of the later roadmap.

## Setup

Python 3.10+ is sufficient for the verifier and JSONL tools. Model runs need a CUDA-capable PyTorch build and the research dependencies. The local setup uses Python 3.12 in `.venv`; it does not change system Python.

```powershell
git submodule update --init third_party/ncm
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -e '.[research,test]'
.\.venv\Scripts\python.exe -m concept_firewall doctor
.\.venv\Scripts\python.exe -m concept_firewall download
```

The CUDA wheel command is the one selected for this machine. Choose a supported build for other hardware using the [official PyTorch installer](https://pytorch.org/get-started/locally/). The upstream MIT source is pinned to `c70274273f489abc73832b2b98584a8483b6b203` and has no local patches. No Anytime NCM runtime was available to reuse: the adjacent project currently has a scaffold only.

`download` fetches only two hard-Sudoku checkpoints and two benchmark files, approximately 164 MB total. It uses immutable Hub revisions and verifies exact size/SHA-256 before use. Remote paths are `sudoku/hard/*`; local paths are `artifacts/sudoku-hard/` and `data/sudoku-hard/`. Other tasks are not downloaded. Loading NCM checkpoints and dataset pickles is restricted by the runner to these reviewed hashes.

## Run

```powershell
.\.venv\Scripts\python.exe -m concept_firewall baseline --config configs/sudoku_smoke.yaml
# Substitute the baseline manifest printed by the previous command:
.\.venv\Scripts\python.exe -m concept_firewall collect --config configs/sudoku_smoke.yaml --baseline-manifest results/manifests/RUN-baseline.json
# Substitute the collection manifest printed by collect:
.\.venv\Scripts\python.exe -m concept_firewall analyze --manifest results/manifests/RUN-collection.json
.\.venv\Scripts\python.exe -m concept_firewall train --manifest results/manifests/FULL-collection.json --protocol configs/probe_protocol.json
.\.venv\Scripts\python.exe -m pytest
```

To reproduce the completed bounded diagnostic study:

```powershell
.\.venv\Scripts\python.exe -m concept_firewall audit --protocol configs/m3_followup.json
# Substitute the audit manifest printed above:
.\.venv\Scripts\python.exe -m concept_firewall followup --audit-manifest results/manifests/AUDIT.json --protocol configs/m3_followup.json
```

The follow-up consumes the locally retained original trajectory/probe artifacts, whose hashes are checked by the audit. On another machine, restore those ignored artifacts from a verified copy or reproduce the original collection and probes; this is not a download-only shortcut. Old run manifests retain their exact commands and source snapshots.

The 32-input smoke configuration reduces batch size from the released 128 to 8 for local memory. It is operational validation, not a statistical accuracy estimate. Baseline executes the actual official evaluator and keeps its logs. Collection requires a successful baseline with the same configuration and verifies every final board against that run. It preserves all 12 levels, code prefixes, pooled tokenizer latents, features and current correctness; final outcome labels are separate.

Use `configs/sudoku_probe.yaml` instead of the smoke config for 2,000-puzzle baseline/collection. `train` requires corrected full-prefix records and sufficient class diversity, so the smoke dataset is intentionally too small for the frozen probe protocol. The protocol fixes four puzzle partitions (50% train, 15% validation, 15% calibration, 20% test), level 6 as the primary comparison, regularization choices and 500 puzzle-bootstrap replicates. Model JSON files are portable; `scripts/verify_probe_artifacts.py --manifest ...` audits their predictions and training-only scaler means.

Generator totals are measured with CUDA synchronization after warmup. Reconstruction happens after full generation; per-level generator timings remain null. These observations do not establish live lead time, monitoring overhead, intervention effects or speedups.

For verifier-only use without ML dependencies:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m concept_firewall verify --puzzle '81-cell puzzle' --board '81-cell completion'
python -m unittest discover -s tests
```

Actual CLI arguments must contain 81 ASCII cells or nine `|`-delimited rows. `0`, `.`, and `_` mean blank; incomplete outputs fail verification. Every clue and every row, column and box must be preserved. Alternative valid solutions are accepted.

## Outputs and scope

Small manifests, reports and figures belong in `results/`. Large raw predictions, JSONL/Parquet trajectories, weights and datasets are ignored. Manifests identify exact commands, source-content hash (also when this new repository has no commit), dependency versions, artifact hashes, parameters and failures. `requirements.lock` is an environment snapshot, not a portable resolver lock.

New run manifests preserve an exact source ZIP and digest before execution, so an uncommitted checkout can still be audited. Older recorded source snapshots are listed in `results/manifests/source_snapshots.json`.

Probes require a validated real observational dataset and frozen puzzle-level splits. Branching, interventions, natural-language tasks and the optional UI retain the design's later evidence gates. See [reproduction status](docs/reproduction_log.md), [experiment protocol](docs/experiment_protocol.md), and [limitations](docs/limitations.md).

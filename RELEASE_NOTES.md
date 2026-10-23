# Sudoku study package 0.1.1

**Scope:** the completed initial M0–M3 observational Sudoku study and one bounded development-only follow-up. This is a reproducibility package, not the design's v1.0 research milestone.

## Findings

- The pinned official evaluator solved **1,725/2,000 puzzles (86.25%)**. Corrected cumulative-prefix capture produced **24,000 observations** with exact final-output equivalence.
- The initial prespecified level-6 pooled-latent addition changed AUROC by **−0.0078**, with paired 95% interval **[−0.0368, +0.0193]**.
- Independent checking matched all current labels and final outcomes. A calibration reversal affected a decoded-only model; the original primary comparison remains negative.
- Two fixed spatial variants were evaluated on 1,600 development puzzles, excluding the original 400 test identities. Neither met the primary continuation criteria. This follow-up is exploratory and supplies no fresh confirmation.

The result supports closing this bounded study. It does not establish that all NCM representations lack correctness information. No branching, online intervention, equal-cost benefit, safety guarantee, or novelty claim was established. M4–M7 remain deferred.

## Contents

- Versioned Python source, tests, frozen protocols, roadmap, reports, figures, manifests, and historical source snapshots.
- A separate checksummed ZIP containing retained corrected trajectories, original probes, follow-up features/models, and official evaluator outputs; weights and official datasets are downloaded separately.
- A Python wheel for the command-line tools. Run model/evidence commands from the complete project checkout, which also supplies configs and the pinned NCM submodule.
- A fresh-checkout reproduction report that states exactly which evidence was replayed and which expensive generation steps were not repeated.

Start with the [reproduction guide](docs/reproduce_study.md), [study closeout](results/reports/sudoku_study_closeout.md), [roadmap](ROADMAP.md), and [source/artifact notices](THIRD_PARTY_NOTICES.md).

The software version is `0.1.1`; it does not mark the roadmap's v0.4/v0.5/v1.0 evidence gates as passed. No paper, hosted service, or paid compute is part of this delivery.

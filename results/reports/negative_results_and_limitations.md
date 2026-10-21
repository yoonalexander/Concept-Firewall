# Negative results and limitations

- The prespecified level-6 pooled-latent increment is −0.0078 AUROC (95% paired puzzle interval −0.0368 to +0.0193): no demonstrated improvement. The latent-only AUROC is 0.4994, close to chance. The shuffled-label control is also compatible with chance.
- Raw-input and input-plus-decoded models underperform chance on this internal test split. Their calibrated ranking was retained as fitted; no test-driven inversion or reselection was performed. Class counts are modest (49 test failures, 44 calibration failures), and model/partition variability remains material.
- Mean pooling discards spatial details. This experiment tests a particular low-capacity representation/probe protocol, not all possible NCM correctness information.
- Decoded-only late-level discrimination is an exploratory result. No actual online cost, remaining generation time, intervention or recovery was measured. Per-level generator timings remain unknown.
- Every corrected pre-final board is incorrect under exact clue-preserving validation. That does not mean its partial constraints contain no information; current correctness is distinct from final correctness.
- Initial short `z_levels` decoding produced unsuitable candidate boards and a weak decoded control. Those experiments are explicitly superseded; corrected snapshots use the upstream accumulator API and pass length, storage, future-independence and final-equivalence tests.
- Exact duplicate clue grids are grouped. Sudoku symmetry-related identities are not audited. Four internal partitions carve up a public official test set; no untouched official probe test score is claimed.
- Bootstrap intervals condition on fitted models and resample puzzle identities. Secondary levels/models have no multiplicity adjustment. Empirical calibration-set FPR budgets do not guarantee test or sequential-policy FPR.
- Baseline execution uses one local Windows GPU, batch size 8, and the recorded environment, rather than claiming exact reproduction of an upstream paper's hardware/runtime setup.
- Sudoku correctness is structural reliability. No harmful-content, privacy, factuality, policy-safety, causal or novelty claim follows.

See [full probe evidence](probe_evaluation.md), [baseline evidence](baseline_reproduction.md), and [reconstruction correction](reconstruction_correction.md). Later phases remain gated.

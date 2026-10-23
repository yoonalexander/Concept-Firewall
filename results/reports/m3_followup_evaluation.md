# Bounded M3 follow-up: completed, continuation criteria not met

**Date:** October 23, 2026. **Decision:** close the current bounded Sudoku experiment with a negative research result. M4–M7 remain deferred; this is not completion of the full project roadmap or proof that no NCM representation can predict errors.

## Audit findings

- An independently implemented checker agreed with all **24,000 current labels** and **2,000 final outcomes**. Every final board still matches the official evaluator. Failure is consistently the positive class. The [agent case walkthrough](m3_manual_case_review.md) records successful, failed, incorrect intermediate and malformed examples.
- The level-6 decoded-only calibrator has slope **−1.2967**. Raw test AUROC is **0.5857** and calibrated AUROC is **0.4143**. Its raw calibration-partition AUROC is **0.4263**, explaining the learned reverse direction. No original model or reported score was changed after seeing this.
- Both members of the original primary comparison have **positive** calibration slopes. Their negative incremental result is therefore not explained away by the decoded-only reversal.
- Input-heavy probes show substantial overfitting: input-plus-decoded training AUROC **0.9963**, validation **0.5665**, calibration **0.5175**, and test **0.4152**. The follow-up consequently includes nested selection of a cheap baseline and separate input-plus-decoded reporting.
- All **102 protected original files** were unchanged. The limited digit-renaming/transpose audit found no duplicate groups among these 2,000 puzzles. This does not audit every Sudoku symmetry.

## Fixed follow-up

The [protocol](../../configs/m3_followup.json) was saved before the audit and fitting. Exactly two new representations were evaluated: **row-pooled projection** and **cell-position projection**. Both use frozen label-independent projections to 256 dimensions, matching the global-mean baseline's dimension. No seed, level or hyperparameter search was expanded after results were observed.

The study used only **1,600 development puzzles**, containing **226 failures**, from the original training, validation and calibration partitions. All **400 original test identities were excluded** from spatial feature capture and all new fitting. Four grouped outer folds assessed each method; two grouped inner folds selected C and the cheap baseline family using log loss. Scaling was fitted within training folds only.

The primary aggregation is the sample-weighted mean of outer-fold AUROC. New discrimination uses raw margins; no new calibration or test-driven sign inversion was performed. Fold definitions were saved before fitting. These are exploratory results on previously exposed development data, not fresh independent confirmation.

| Model | Level 6, primary | Level 11, secondary |
|---|---:|---:|
| Decoded-board control | 0.5017 | 0.6857 |
| Input + decoded control | 0.5583 | 0.5905 |
| Selected cheap control | 0.5017 | 0.6857 |
| Selected cheap + global mean | 0.5415 | 0.6789 |
| Selected cheap + row projection | 0.5636 | 0.6451 |
| Selected cheap + cell projection | 0.5676 | 0.6143 |

At level 6, the row and cell additions improve on the selected cheap control by **0.0619** and **0.0659**, but their prespecified 97.5% paired intervals are **[−0.0109, +0.1341]** and **[−0.0016, +0.1344]**. Both include zero. Their gains over mean pooling are only **0.0220** and **0.0260**, and their absolute AUROC is below the declared 0.65 candidate threshold. Neither meets the candidate criteria.

The cheap-family selector chose decoded-only in all folds based on inner log loss. That selection objective is not AUROC maximization: the separately reported input-plus-decoded control reaches 0.5583 at level 6, already close to the spatial variants. The larger lift over the selected control should not be presented as robust superiority over every simple baseline.

At level 11, adding row or cell features lowers AUROC by **0.0406** and **0.0714** relative to the cheap decoded control, with negative lift in all four folds. This secondary result favors retaining the simple board diagnostics in this experiment; it is not evidence of an effective live policy.

Intervals resample puzzle groups within each outer assessment fold and condition on the fitted models. Models are not refitted inside the bootstrap. The 97.5% primary coverage reflects two declared primary comparisons; fold/selection uncertainty and repeated use of the development dataset limit interpretation. Secondary-level results are exploratory.

## Compute, reproduction and fresh data

Only cached prefix codes were reconstructed. No generation run, new checkpoint download, paid compute, transformer hook or intervention was added. Offline feature capture took **6.45 seconds** and CPU fitting/evaluation **23.73 seconds**, excluding environment loading and the label audit. These are job costs, not an inference speedup.

The first capture attempt at batch size 32 was rejected by the exact-decode guard before fitting. Repeating capture at the original recorded batch size 8 restored exact agreement for all 3,200 selected-level development reconstructions and their global means. The failed attempt is retained in manifest `20261023T122423561703Z-m3-followup.json`; it produced no probe result and was not used for model selection.

The [official-release inventory](../manifests/m3_followup_data_inventory.json) still contains only the same 2,000 hard-Sudoku puzzles and solutions. No unused hard split was available there. External puzzle sources were not exhaustively surveyed. Repartitioning or transforming these puzzles would not create fresh independent confirmation; a new source would also need provenance, overlap, checkpoint-training exposure and distribution checks.

Reproduction commands:

```powershell
.\.venv\Scripts\python.exe -m concept_firewall audit --protocol configs/m3_followup.json
# Substitute the new audit manifest emitted above:
.\.venv\Scripts\python.exe -m concept_firewall followup --audit-manifest results/manifests/AUDIT.json --protocol configs/m3_followup.json
.\.venv\Scripts\python.exe -m pytest -q
```

Evidence:

- [Complete independent audit](20261023T121711278798Z-m3-audit.md) and [audit manifest](../manifests/20261023T121711278798Z-m3-audit.json).
- [Complete follow-up report](20261023T122529782263Z-m3-followup.md), [run manifest](../manifests/20261023T122529782263Z-m3-followup.json), and [saved nested fold identities](../manifests/20261023T122529782263Z-m3-followup-folds.json).
- Feature/projection digests, frozen source ZIP, per-fold C choices, average precision, uncalibrated Brier scores and conditional intervals are in the run manifest. Large features, model parameters and assessment margins remain in the ignored local probe directory.
- [Original result](probe_evaluation.md) remains unchanged; see [scoped study closeout](sudoku_study_closeout.md) for the resulting decision.

Method references: [scikit-learn calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) and [evaluation/model-selection guidance](https://scikit-learn.org/stable/modules/cross_validation.html).

# V2-3: bounded generator-signal study

**Execution:** completed. **Scientific decision:** no candidate meets the frozen development criteria; close this study at the V2-3 gate. The 1,600 confirmation puzzles remain unused by the model. No confirmation, online monitoring, recovery, or intervention benefit is established.

## What was built and tested

The [frozen study](../../configs/v2_study.json) was executed once on the [new-source cohort](v2_data_validation.md), using the verified observational wrapper and the existing unchanged checkpoint. It captured one normalized generator representation at level 6, projected to 256 fixed position-aware features, plus six predeclared confidence summaries. Only train/validation/calibration roles were loaded. No layer, level, projection seed, feature width, classifier family, or hyperparameter grid was expanded after outcomes were observed.

The [run manifest](../manifests/20261025T030127575557Z-v2-study.json) retains the exact code snapshot, protocol/data hashes, validation halves, chosen controls and regularization, operating thresholds, feature/model hashes, metrics, and resource ledger. Four cheap model families each received two choices; the activation candidate received two choices. Five final models were refitted on training+validation only. One training-label permutation was diagnostic only. **All 16 allowed fits were used**, with no calibration or bootstrap refits.

## Data actually evaluated

| Role | Puzzles | Final failures | Final successes |
|---|---:|---:|---:|
| Training | 4,000 | 2,458 | 1,542 |
| Validation | 1,600 | 970 | 630 |
| Calibration/development gate | 800 | 493 | 307 |
| Sealed confirmation | 1,600 | Not generated | Not generated |

The new-source development failure rate is **3,921/6,400 (61.27%)**, substantially above the legacy planning rate of 13.75%. The input distribution differs from the official fixed-30-clue benchmark. This is a new-source experiment, not a direct comparison with old benchmark accuracy. The planning assumption did not transfer; it must not be repaired by changing confirmation counts or criteria after observing outcomes.

## Development operating points

These are metrics on **800 calibration puzzles**, the same partition used to set the negative-score thresholds and apply the development gate. They are exploratory development evidence, not fresh-confirmation performance. Each family uses its own frozen calibration rule; exactly 15 of 307 eventually correct answers triggered an alert at each selected operating point.

| Model | AUROC | Mistakes detected | Recall | False alarms |
|---|---:|---:|---:|---:|
| Partial-board diagnostics | 0.5243 | 26/493 | 5.27% | 15/307 (4.89%) |
| Input + board | 0.5361 | 37/493 | 7.51% | 15/307 (4.89%) |
| Board + confidence | **0.7108** | **111/493** | **22.52%** | 15/307 (4.89%) |
| Input + board + confidence | 0.6813 | 99/493 | 20.08% | 15/307 (4.89%) |
| Selected confidence control + activations | 0.6876 | 94/493 | 19.07% | 15/307 (4.89%) |

The validation selection rule chose board+confidence as the activation base and the confidence-only fallback. Confidence clearly supplied more useful development discrimination than board/input controls here. Adding the tested activation projection reduced recall by **3.45 percentage points** and AUROC by **0.0232** relative to that confidence control.

The practical target was at least **40% recall**, at no more than 5% observed false alarms, plus the required incremental gain. The activation and confidence-only candidates both fall short of 40%. The activation candidate also fails its incremental comparison. No candidate was frozen, and no confirmation outcome was inspected to rescue either branch.

## Uncertainty and overfitting diagnostics

The [diagnostic sidecar](../v2/contracts/v2-development-diagnostics.json) reports raw-logistic probability loss/Brier scores, refit-population discrimination, and 2,000 paired failure-puzzle bootstrap draws. Board+confidence minus input+board has a descriptive recall lift of **15.01 points**, with conditional pointwise 95% interval **[10.75, 19.47]**. Activations minus board+confidence has lift **−3.45 points**, interval **[−6.29, −0.61]**.

Those intervals condition on the fitted models and thresholds chosen on this same calibration partition. They omit selection, fitting, and threshold uncertainty; they are not familywise or independent-confirmation claims and did not influence candidate selection. No interval overrides the failed practical target.

Input+board had refit-population AUROC 0.7299 versus calibration AUROC 0.5361. Board+confidence was 0.7471 versus 0.7108; the activation model was 0.7790 versus 0.6876. Input-heavy fitting still showed a substantial generalization gap. The single shuffled-label diagnostic had validation AUROC **0.4776**. This is a sanity check, not proof of absence of every leakage route.

## Artifact and label verification

- [Portable artifact audit](../v2/contracts/v2-study-artifact-audit.json): all five saved models reproduce their 800 calibration operating predictions, and their scalers match training+validation-only means. All capture/model hashes match. The working scientific code matched the run's retained source digest at audit time.
- [Independent outcome audit](../manifests/20261025T030920192150Z-v2-outcome-audit.json): all **6,400 outcomes and current-board feature records matched** when replayed with the unobserved generator. The audit retained raw full codes/current/final boards and independently checked the final constraints. This is verification within the same budget, not another detector fit or a new hypothesis.
- The original study manifest and historical M0–M3 evidence remain unchanged. Large features, models, and raw predictions remain ignored, with paths and SHA-256 in manifests.
- The implementation verification passed **107 tests and 129 subtests**, and `pip check` passed. New fitting tests cover threshold ties/FPR accounting, all-comparator gates, separated validation halves, input framing, training-only scaling, and exact fit-job charging.

The final cumulative ledger charged **226.23 GPU-assisted elapsed seconds**, **4.77 CPU fitting seconds**, 16 fits, and **17,802,592 retained feature/model/raw bytes**, including pilot, capture, loading, and the independent outcome audit. These conservative charges include host work and are not a live monitoring overhead/speedup measurement. No paid compute, additional checkpoint, subagent, or confirmation input was used.

## Reproduction and stopping decision

Scientific execution command: `.venv\Scripts\python.exe -m concept_firewall v2-study`. The command refuses an unplanned repeat if a study attempt already exists. It does not reset the persistent allowance. New hyperparameter fitting under this study is prohibited because the 16-fit cap is consumed.

Independent replay command: `.venv\Scripts\python.exe scripts/audit_v2_outcomes.py --manifest results/manifests/20261025T030127575557Z-v2-study.json`. Restore the exact frozen source partitions with the documented V2-2 command and copy the ignored feature/model artifacts using their recorded hashes before auditing another machine. Audit generation consumes remaining GPU allowance; it must not reset a ledger or open confirmation. The raw outcome path and digest are retained in the audit manifest.

The local `dist/v2-generator-signals-v1-evidence.zip` packages all 15 ignored cohort, feature, model, raw-outcome, and consumed-ledger files: **13,260,183 compressed bytes**, archive SHA-256 `621a51db0763466886a672c90591050755ea25a3d6a328d12cbb7f829eb327b7`. The [inventory](../v2/contracts/v2-evidence-inventory.json) freezes every member hash. Exact restoration of all 15 files was verified in a separate empty destination. Restore into a clean Git checkout with `.venv\Scripts\python.exe scripts/v2_evidence.py restore --archive PATH-TO-ZIP`; all hashes are checked before writes, and conflicting files are preserved. Keep the restored ledger's consumed counters. The original 174-file study archive also passed its unchanged restoration checks after the archive utility was extended. The ZIP is a local delivery artifact, not a GitHub Release asset or a claim of completed V2-8 clean-environment/release work.

**Decision:** retain the confidence finding as exploratory evidence and close the current detector study. Do not lower the target, try more projections, spend the remaining GPU allowance on a search, or open confirmation for curiosity. V2-4 through V2-7 remain unstarted. This does not establish that every activation representation or every future warning method is ineffective. Any further experiment needs a new scoped question, budget, and independent confirmation plan.

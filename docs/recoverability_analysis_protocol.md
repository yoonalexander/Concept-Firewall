# Recoverability analysis protocol

This is a separate authorized exploratory question using exposed saved records. It cannot provide independent confirmation and does not amend the failed V2 or confidence-allocation gates.

The executable specification is `configs/recoverability_analysis.json`; artifact sizes and SHA-256 hashes are in `results/recoverability/inventory.json`. Only the paired 1,600-puzzle recovery cohort has action-specific potential outcomes. All 1,600 group IDs are distinct. Original failures number 1,010. The other exposed cohorts cannot supply supervised recoverability labels without new generation, so are excluded.

Phase 1 freezes the action-specific targets, feature boundary, five grouped folds, 40 fixed fits, 600 CPU seconds and 1,200 wall seconds before fitting. Phase 2 implements and tests the specification without research fitting. Phase 3 runs once and reports even negative findings. No subagents, paid compute, checkpoint search or new model output is permitted.

Decision-time features are collected at level 6 and retained until final exact verification determines retry eligibility. Verification is an eligibility operation, never a recovery predictor. Outcomes only form action-specific targets and evaluate selections. Models learn recovery among failures, rather than merely learning the original error label.

The primary model and 272-retry gate are fixed in the JSON. All secondary models, budgets and controls are disclosed; no winner is relabeled primary. The group bootstrap conditions on OOF scores and masks and cannot recover independent confirmation or include fitting instability. Service costs reuse historical local measurements and explicitly leave new scorer latency unmeasured.

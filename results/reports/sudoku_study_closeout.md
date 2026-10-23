# Scoped Sudoku study closeout

**Closed:** October 23, 2026. **Scope:** the initial M0–M3 Sudoku experiment plus the bounded diagnostic/spatial follow-up. **Outcome:** useful incremental latent failure prediction was not demonstrated under the tested protocols.

This closes the current experiment rather than the entire Concept Firewall roadmap. Branching, live interventions, natural-language evaluation and an optional viewer remain deferred. No v1.0 release, production safety system, novelty claim or successful recovery policy is declared.

## What was established

1. The pinned official NCM evaluator runs locally: 1,725/2,000 hard puzzles solved (86.25%) under the documented environment/batch deviation.
2. Full cumulative-prefix collection can preserve all 12 levels and exact final-output equivalence. Corrected observations contain 24,000 records.
3. Strict clue-preserving labels passed adversarial tests, independent full-data checking and an agent case walkthrough. Invalid intermediate boards can become valid at the final level.
4. The original frozen level-6 comparison was negative: adding pooled latents changed AUROC by −0.0078, with 95% interval [−0.0368,+0.0193].
5. The diagnostic audit found a decoded-only calibration reversal and severe overfitting in input-heavy probes; it found no label-orientation discrepancy and did not invalidate the original primary comparison.
6. Two fixed spatial representations were evaluated once on development data. Neither met the prespecified primary candidate criteria. At level 11, adding them performed worse than cheap decoded-board diagnostics.

## What was not established

The work does not establish that every NCM representation lacks correctness information. Mean pooling and fixed projections are limited representations; no transformer-state study, causal intervention, stochastic recovery, real online lead time or equal-cost benefit was tested. The dataset contains only 49 failures in the original internal test split, and the follow-up reuses exposed development data.

The source, weights, artifact revisions, generation parameters, exact commands, environment, original/updated protocol hashes and test identities are retained. Old results and superseded experiments were preserved. Bootstrap intervals are conditional on fitted models and do not represent every source of uncertainty. No unused official hard-Sudoku split was found in the checked release; broader external dataset provenance remains unresolved.

## Decision

Stop the current representation search and retain these negative findings. Do not spend further compute on additional seeds, larger probes, branching or an interface as part of this bounded study. A future study would require a separately specified question and protocol, suitable fresh confirmation data, and a justification for the additional cost. Late-level board diagnostics may be a useful future baseline, but their observational discrimination does not by itself justify a live intervention system.

## Reproduction and remaining project work

Start with [baseline reproduction](baseline_reproduction.md), [corrected trajectory analysis](level_trajectory_analysis.md), [original probes](probe_evaluation.md), and [bounded follow-up](m3_followup_evaluation.md). The [roadmap](../../ROADMAP.md) preserves the uncompleted phases and formal release tasks. Source ZIPs and SHA-256 digests are recorded in the experiment manifests; weights/datasets/raw features are intentionally not ordinary Git contents.

A formal release still needs the fresh-checkout/environment reproduction gate, final packaging/versioning, and any intended literature/novelty audit. This local scoped closeout report is not a claim that those remaining release requirements have passed.

# Clean-checkout reproduction — Sudoku study 0.1.1

**Completed:** October 23, 2026. **Outcome:** passed for the documented Windows environment and retained-evidence replay. The tested implementation commit is `e7b3d242cc60a3d39b3e7c8f1f05e079e38787e6`; later delivery commits add reports and packaging metadata.

## Verified scope

1. Cloned the pushed repository and the pinned NCM submodule into an isolated checkout, then advanced it to the packaging commit. No original working source or original virtual environment was used by the replay.
2. Created a new Python 3.12.10 virtual environment, installed the recorded requirements from the public indexes, and installed the built `0.1.1` wheel. The installed package resolved inside that new environment. `pip check` passed.
3. Ran all **87 tests and 119 subtests**, with no skips, against the clean checkout and new dependency environment.
4. Restored **174 retained evidence files** from the checksummed archive. All member hashes matched. Separate preflight checks rejected a corrupt inventory and conflicting destination content before changing that content.
5. Downloaded all four official hard-Sudoku files into the clean checkout, using the documented command. Every exact size and SHA-256 matched the pinned specification.
6. Loaded each of five saved primary-level probe families, reproduced all **400 held-out predictions per family** within `1e-12`, and checked training-only scaler means.
7. Independently checked **24,000 current labels and 2,000 final outcomes/official outputs**. Protected original evidence remained unchanged.
8. Replayed the fixed two-representation, two-level follow-up. **Every nested result value matched exactly**, including fold metrics, model selections, intervals, and continuation decisions. Protocol, fold, feature, and projection hashes matched the original run. Prefix capture took 6.66 seconds; fitting/evaluation took 21.02 seconds, excluding loading/auditing.
9. Verified all **seven retained source ZIP digests** and local Markdown report links. Reviewed pinned source/model/dataset licensing statements and recorded the project-license boundary in the [notices](../../THIRD_PARTY_NOTICES.md).

## Evidence

- [Machine-readable reproduction summary](../manifests/clean_checkout_reproduction.json)
- [Portable probe replay](../manifests/clean_checkout_probe_validation.json)
- [Independent replay audit](../manifests/20261023T181914911947Z-m3-audit.json)
- [Follow-up replay](../manifests/20261023T182007348503Z-m3-followup.json) and [fold identities](../manifests/20261023T182007348503Z-m3-followup-folds.json)
- [Retained-evidence inventory](../manifests/sudoku_study_artifacts.json)
- [Reproduction commands](../../docs/reproduce_study.md)

The delivery folder contains `sudoku-study-artifacts.zip` (185,827,369 bytes) and `sudoku-study-reproduction.zip` (16,857,260 bytes), plus the source ZIP, wheel, and `SHA256SUMS`. The reproduction ZIP retains the new manifests, reports, feature/model artifacts, source snapshot, and command logs. Its hash is in the machine-readable summary. The original evidence bundle remains separate and unchanged. Large ZIPs are delivered locally rather than committed to ordinary Git history.

## Limits and decision

This check restores original evidence and repeats its audits and fixed offline fit on the same host/GPU. It does **not** repeat full baseline/trajectory generation, supply fresh puzzles, establish cross-hardware determinism, or constitute independent scientific replication. Dependency versions are a tested machine snapshot, not a portable hash-locked resolver. No publication or novelty claim is made, and no project-wide license is newly selected.

The scoped reproducibility delivery passes. The scientific result remains negative; M4–M7 stay deferred. This package does not declare the design's v1.0 milestone complete.

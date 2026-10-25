# V2-2: independent project data and frozen partitions

**Decision:** pass for the declared new project cohort. No model has generated answers on these puzzles in this phase, and checkpoint-training independence is unknown.

The [source review](../v2/contracts/v2-source-review.json) followed the frozen order: no unused hard split was present in the pinned official release; two external candidates were reviewed. The first [candidate card](https://huggingface.co/datasets/certen/Sudoku-1M-Puzzles/blob/f993a28fb8b120bd842e11700314f0f384b4c29d/README.md) describes a single seed-board family and random blanking and was excluded for this confirmation purpose. The selected [Sudoku Exchange source](https://github.com/grantm/sudoku-exchange-puzzle-bank/tree/d8c8ebaee0c08c412cfba96af1923dfa61c83317) contains computer-generated puzzles with source ratings and a public-domain data dedication. Only its `hard.txt` bucket was selected. Selection did not use model outcomes.

The [data manifest](../v2/contracts/generator-signals-v1-data.json) freezes revision `d8c8ebaee0c08c412cfba96af1923dfa61c83317`, immutable Git-blob hashes for source/readme/license, exact group and puzzle identities, ordered partition files, and SHA-256 digests. [Execution](../manifests/20261025T025503252866Z-v2-data.json) took **33.07 seconds** of data preparation with no checkpoint load, model generation, or fit.

## Validation and grouping

All **8,000 selected puzzles** passed independent bit-mask minimum-remaining-values enumeration with exactly one solution. The source's uniqueness assertion was not accepted without checking. The fixed validation cap was 9,000 candidates/900 seconds/100,000 search nodes per puzzle; all first 8,000 candidates qualified, so no replacements or outcome filtering occurred.

A colored clue-graph invariant groups every standard digit renaming, allowed row/column/band/stack permutation, and transpose into the same signature. The graph uses shared row/column and band/stack node colors and unlabeled digit nodes. Such Sudoku transformations are graph isomorphisms, so the six-iteration Weisfeiler–Lehman hash cannot split them into different groups. Hash collisions or additional graph equivalences conservatively merge unrelated puzzles. This is an invariant grouping rule, not a complete minimal canonical form.

The audit excluded every group matching any of the **2,000 legacy puzzle groups** and retained one puzzle per new group. All 8,000 selected groups are distinct and disjoint from the legacy signatures. Tests exercise the generators of each standard symmetry, inconsistent/ambiguous puzzles, solver limits, partition digest changes, sealed confirmation access, and restoration conflicts.

## Frozen roles and limits

| Role | Puzzle/group count | Access before candidate freeze |
|---|---:|---|
| Train | 4,000 | Fitting allowed after V2-3 checks |
| Validation | 1,600 | Declared selection only |
| Calibration | 800 | Final operating thresholds and development gate only |
| Confirmation | 1,600 | No feature capture, answer generation, or candidate evaluation before freeze |

The partition loader denies confirmation by default. This is workflow isolation, not an operating-system access-control claim: data curation necessarily processed input rows, but did not generate final model outcomes or use them to select the cohort. Confirmation identities cannot be moved or replaced after outcome inspection.

The selected rating range is 2.5–4.7 and clue counts are 22–36, versus exactly 30 clues in all official legacy puzzles. This is a new-source cohort, not an exact replication of the old input distribution. The old failure-rate planning assumption may not transfer. If final confirmation contains fewer than the required 150 failures or 1,000 successes, the result is inconclusive; neither sample size nor criteria may be changed to obtain a positive result. Public source provenance does not establish absence from checkpoint training.

**Verification:** 103 tests and 129 subtests passed. Exact partition restoration from the pinned source was also executed in a separate temporary directory and reproduced all four frozen input-file digests. The ledger charged 8,000/8,000 new cohort identities; model GPU budget remains the pilot's 5.62 seconds and fit count remains zero.

## Commands

Initial cohort creation (already executed): `.venv\Scripts\python.exe -m concept_firewall v2-data --source .tmp/v2-source-bank`.

For another checkout, clone the source, check out the pinned revision, and run `.venv\Scripts\python.exe -m concept_firewall v2-data --source PATH-TO-SOURCE --restore`. Restoration reads the immutable source Git blob, rebuilds exactly the recorded partitions, and refuses conflicting existing content. It performs no reselection or model calls. Data stay outside ordinary Git; frozen source/partition manifests are committed.

**Next:** V2-3 may capture signals and fit the single bounded comparison on train/validation/calibration only. The 1,600 confirmation puzzles remain closed until a qualifying candidate is frozen.

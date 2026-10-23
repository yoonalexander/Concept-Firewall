# Agent case walkthrough: Sudoku labels

Reviewed October 23, 2026. This is an agent-conducted spot check of raw inputs, reconstructions and explicit constraint witnesses, not independent human annotation or a statistically representative sample.

The [full audit](20261023T121711278798Z-m3-audit.md) contains the literal input/output strings and every independent witness. Its checker matched all 24,000 current labels and 2,000 final labels without calling the production parser/verifier. Cases below were selected deterministically by category.

| Case | Puzzle identity | Level | Walkthrough and conclusion |
|---|---|---:|---|
| Successful final board | `65ba81b5b983dbfb5143472178bd02077fd9c9ae7123ba4cc55532f9bb3f27be` | 12 | Input row 1 is `_216_7_85`; output is `921647385`, preserving clues at columns 2, 3, 4, 6, 8 and 9. Column 1 is `9,7,5,4,1,8,2,6,3`, and the upper-left box contains `9,2,1,7,6,4,5,8,3`, each covering 1–9. The independent full-grid check finds no missing cells, clue changes or conflicting units. Accept. |
| Failed final board | `80887d82a1e3b0258cb9b1f8cafc90d60d444cf504c7d3a1aa9fb076ca97aed3` | 12 | Output row 3 is `671992384`: columns 4 and 5 both contain 9, and 5 is missing. All original clues are preserved, showing why clue preservation alone is insufficient. The row conflict is enough to reject this completed board. |
| Incorrect intermediate board | `65ba81b5b983dbfb5143472178bd02077fd9c9ae7123ba4cc55532f9bb3f27be` | 6 | Output row 1 is `117624988`, with repeated 1 and 8. Input clue R1C2 is 2, but the output has 1. The output has the full parseable shape and no blanks, yet violates both clues and Sudoku constraints. Reject its current correctness; this trajectory's eventual final output is nevertheless correct. |
| Malformed intermediate board | `a5271ebdddbecf2f10e36c8fb0a1778c08e4fdc1a4b636237e92c3fe3964922c` | 3 | The raw output has 89 digit characters and no row separators. It is neither a compact 81-cell board nor nine 9-cell rows. Reject as malformed; do not truncate or silently extract a valid-looking subset. |

The cases support the distinction between current and final correctness, preserve malformed outputs as failures, and demonstrate both clue and structural checks. No label discrepancy was found. Manual case-review bookkeeping for M2 is now recorded with this explicit agent-review qualification.

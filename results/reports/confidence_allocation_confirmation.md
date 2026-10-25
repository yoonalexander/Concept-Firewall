# Fixed confidence allocation confirmation

The separate `confidence-allocation-v1` allocation screen passed. The original V2 40% recall study remains failed and closed. This result confirms a limited-coverage failure-enrichment signal, not a recovery or compute advantage.

The [protocol](../../configs/confidence_allocation.json), [contract](../../docs/confidence_allocation_contract.md) and byte-identical saved probe were committed and pushed in `884f2fe` before any confirmation model outcomes were generated. The confidence-only live monitor first reproduced all codes and saved feature vectors on eight already exposed calibration puzzles. All confirmation outcomes were checked by two independent Sudoku constraint implementations. No probe fitting, threshold change or candidate substitution occurred.

| Measurement | Confirmation result |
|---|---:|
| Puzzles | 1,600 |
| Original successes / failures | 590 / 1,010 |
| Fixed alerts | 272 (17.00%) |
| Alerted failures | 242 |
| Alert precision | 88.97% |
| Failure recall | 23.96% |
| False alarms among successes | 30/590 (5.08%) |
| One-sided 95% Wilson FPR upper bound | 6.79% |
| Perfect-recovery allocation advantage over random-all | 4.39 percentage points |
| One-sided 95% bootstrap lower bound on that capacity | 3.77 percentage points |

All six preregistered screen conditions passed. The observed FPR is slightly above 5%; the separate allocation study's frozen requirement is a one-sided upper bound at most 8%. This does not satisfy, amend or replace the original study's observed-FPR/40%-recall requirements. The capacity statistic assumes a hypothetical perfect retry; it is not measured accuracy improvement. The exact conditional enrichment p-value is descriptive, not a replacement for the primary bootstrap criterion.

The cohort is now consumed and cannot serve as fresh confirmation again. Checkpoint training exposure remains unknown. Full input/prefix/code/board/score/outcome records are retained in the ignored raw file, with its digest in [confirmation.json](../continuation/confirmation.json). The [run manifest](../manifests/20261025T210517126329Z-allocation-confirmation.json) retains executed source and environment. The separate ledger charged 31.19 GPU-assisted elapsed seconds and 1,616 puzzle generation calls, including the calibration checks. The historical V2 ledger was unchanged.

Proceed to the preregistered recovery comparison: one fixed-prefix stochastic suffix attempt, with the single full-restart alternative only if the primary fails. Include measured monitor cost and verifier-first selection. No additional fitting or parameter search is authorized by this screen.

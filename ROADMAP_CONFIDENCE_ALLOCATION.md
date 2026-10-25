# Confidence allocation follow-on

This is a separately scoped follow-on authorized after the V2 stopping decision. The original V2 40% recall study remains failed and closed. No new result rewrites its gate. Use the same checkpoint and saved board+confidence probe; no new fits or hyperparameter search.

| Step | Deliverable | Status |
|---|---|---|
| 1 | Saved-result value bounds and stronger-baseline check | Complete; [report](results/reports/confidence_value_check.md) |
| 2 | Freeze a narrower allocation protocol, then evaluate the untouched 1,600 project confirmation puzzles once | Complete; [allocation screen passed](results/reports/confidence_allocation_confirmation.md), cohort now consumed |
| 3 | If confirmed, measure monitoring cost and actual fixed-policy recovery against random-all and verifier-first under matched budgets | Complete; [both recovery policies failed the benefit gate](results/reports/confidence_allocation_recovery.md) |
| Practical alternative | Verify proposed Sudoku answers and fall back to bounded exact constraint solving | Complete; [6,400/6,400 exposed development inputs verified](results/reports/verified_sudoku_fallback.md), zero new model calls |
| Closeout | Verify evidence restoration, document outcomes and limits, commit and push | Complete; [closeout](results/reports/confidence_allocation_closeout.md), clean-source restored audit passed with no model calls |

Step 1 found potential value against random-all allocation, but exact Sudoku verification supplies a stronger baseline: retries chosen from verified failures. A confidence score must improve actual recovery enough to offset its false alarms and monitoring cost. Identical deterministic retries cannot improve any answer.

If a scientific gate fails, preserve that finding and complete the applicable alternative analysis and reproducible closeout. Do not replace failed thresholds with easier ones or use the same exposed confirmation outcomes as a fresh test. No paid compute, new checkpoint, subagents, UI or NLP expansion is in scope.

## Final state

All scoped steps and the authorized practical alternative are complete. Fixed alerts confirmed failure enrichment at limited coverage; both neural retry methods failed the comparative benefit gate. The standard-library `solve` command supplies exact-constraint recovery for Sudoku, with explicit failure/search-cap results. The project does not claim learned early-intervention value or general AI safety effectiveness.

Verification: 121 tests and 133 subtests passed; dependency check passed. The seven-file evidence archive restored twice into clean committed source and independently audited 1,600 original outcomes, 3,200 neural retries and 6,400 practical fallback outcomes. Existing dependency packages were reused; no fresh-environment model reproduction is claimed. No further experiments are selected under this roadmap.

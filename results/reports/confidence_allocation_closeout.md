# Completed confidence allocation follow-on

All three recommended steps, the predeclared neural alternative, the practical exact-Sudoku alternative and evidence closeout are complete. No further experiment is selected under this scoped roadmap. Original study failures and ledgers remain preserved.

| Step | Outcome | Committed and pushed |
|---|---|---|
| Saved-results value check | Potential allocation value; exact final verifier identified as stronger baseline | `d93d762` |
| New protocol frozen before outcomes | One unchanged confidence probe, fixed thresholds, no fits, bounded recovery alternatives | `884f2fe` |
| Independent project-held-out screen | 242 failures in 272 alerts; 88.97% precision, 23.96% recall | `9e3fc0f` |
| Actual recovery comparison | Fixed-prefix and full-restart methods failed comparative benefit criteria | `848ac70` |
| Practical reliability alternative | Exact fallback retained 2,479 valid answers and completed 3,921 failed ones on exposed development inputs | `139e066` |

The [confirmation report](confidence_allocation_confirmation.md) establishes limited-coverage failure enrichment. [Recovery](confidence_allocation_recovery.md) establishes no useful confidence-allocation advantage under the two tested policies. At 272 retries, confidence recovered 9 failures with a fixed prefix versus 16.97 expected under verifier-first selection; full restart recovered 21 versus 28.28 expected. Monitoring added about 6.96% mean synchronized service time in the scoped local test. The original 40% recall detector gate remains failed; it was not relaxed or reopened.

The [practical fallback](verified_sudoku_fallback.md) is usable through `python -m concept_firewall solve`. It verified 6,400/6,400 already exposed development inputs, with bounded exact constraint search and no model/GPU dependency. This is a classical Sudoku solver baseline, not evidence that learned early warnings or NCM intervention succeeded. Inconsistent or harder arbitrary inputs can return explicit invalid, unsatisfiable or search-budget-exhausted results.

## Verification and delivery

- **121 tests and 133 subtests passed**; `pip check` passed. Workspace-local temporary storage resolved the sandbox's default temporary-directory permission errors.
- The independent artifact audit checked 1,600 original held-out outcomes, 3,200 stochastic retry outcomes and 6,400 exact-fallback outcomes: **11,200** records total, with zero new model calls or fits.
- The local evidence archive contains seven files, **5,290,692 bytes**, SHA-256 **`389d68a440e388c70af4a034c39d95c4cfd887d80be8899f9287a48ca2951764`**. Its [inventory](../continuation/evidence_inventory.json) is committed; the ZIP is at `dist/confidence-allocation-v1-evidence.zip`, outside Git, without a GitHub Release upload.
- A clean Git source archive imported its own code, restored every member twice, and passed the full retained-data audit without inference. The [replay record](../continuation/replay_verification.json) states the exact source revision, closeout additions and environment boundary. Dependencies were reused; this is not a fresh-environment model reproduction.
- The separate scientific ledger charged **510.32 GPU-assisted elapsed seconds**, **4,936 puzzle generation calls**, zero fits and 5,952,740 raw-record bytes. No paid compute, new checkpoint or subagents were used. Practical fallback validation used CPU only and made zero new model calls.

Use the [reproduction guide](../../docs/reproduce_confidence_allocation.md) for restoration and auditing. The confirmation cohort is now consumed. Scientific commands refuse repeated attempts; no additional thresholds, temperatures or projection searches are pending. The final closeout commit adds only packaging/replay tooling, inventories and documentation after the implementation commits above.

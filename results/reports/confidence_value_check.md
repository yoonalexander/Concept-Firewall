# Saved-results value check

The original V2 study remains closed at its failed detector gate. This analysis uses only its saved 800 calibration rows and the unchanged board+confidence probe. It reproduces 111 detected failures and 15 false alarms; no fitting, GPU generation or confirmation access occurred.

## What the signal could buy

Alerts cover 15.75% of puzzles and contain 88.10% failures, compared with 61.62% overall. A hypothetical perfect retry could add at most 13.88% accuracy. Against randomly allocating the same number of retries across all puzzles, its hypothetical advantage ceiling is 4.17% of puzzles.

Those are bounds, not observed improvements. An identical deterministic retry changes nothing. A retry needs a different sampling policy, and preserving an already valid first answer prevents damage. With zero monitoring cost and retry cost equal to one baseline solve, recovery of approximately 44% of alerted failures would be needed merely to improve correct answers per unit compute. Actual monitoring costs raise this requirement.

## The stronger baseline

Sudoku has an exact final verifier. A verifier-first policy can spend every retry on a failure. Confidence selection has 88.10% failure precision, so its selected failures would need roughly 1.135 times the recovery probability of verifier-selected failures to offset those wasted retries, before monitoring overhead. The same recovery probability everywhere favors verifier-first. Early failure discrimination alone cannot establish value.

## Decision

Proceed with one separately registered study of the already saved board+confidence score. First confirm that its fixed alerts enrich failures over random allocation at a bounded alert rate. If that passes, evaluate one fixed stochastic continuation policy and compare actual solved outcomes with random-all and verifier-first at matched retry counts. Count recomputed prefixes and monitoring work; do not call this an efficient prefix-resume implementation. No new probe fits, layers, thresholds or temperature search.

The confirmation question is narrower than the old 40% recall claim. No new result can turn the old failed gate into a pass. Unsuccessful recovery should close this follow-on with the stronger baseline identified, rather than trigger more detector fishing.

Detailed scenario assumptions, costs and source hashes: [value_check.json](../continuation/value_check.json). Reproduce: `.venv\Scripts\python.exe scripts/check_confidence_value.py`.

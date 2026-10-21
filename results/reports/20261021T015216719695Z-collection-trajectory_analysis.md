# Measured trajectory analysis

Run: `20261021T015216719695Z-collection`. Manifest: `results\manifests\20261021T015216719695Z-collection.json` (SHA-256 `d840813433b83c79402694e261d1334719fa722bae76f1023dcfba62ec79ae08`). Source snapshot hash: `2ac472dc63e2ec4c845b0059fc014a2cfc18a37423519a35ee6ea536f66f0d5b`.

Observed 2000 trajectories / 2000 unique puzzles, each with 12 levels. Final clue-preserving valid completions: 1725/2000. Every final output matches the official baseline.

These are full-depth, post-hoc observations. No per-level generator timing, live lead time, intervention benefit or speedup was measured. A smoke subset does not establish statistical probe performance.

| Level | Unique puzzles | Current correct | Malformed |
|---:|---:|---:|---:|
| 1 | 2000 | 0/2000 | 0 |
| 2 | 2000 | 0/2000 | 0 |
| 3 | 2000 | 0/2000 | 1 |
| 4 | 2000 | 0/2000 | 1 |
| 5 | 2000 | 0/2000 | 1 |
| 6 | 2000 | 0/2000 | 1 |
| 7 | 2000 | 0/2000 | 1 |
| 8 | 2000 | 0/2000 | 1 |
| 9 | 2000 | 0/2000 | 1 |
| 10 | 2000 | 0/2000 | 1 |
| 11 | 2000 | 0/2000 | 0 |
| 12 | 2000 | 1725/2000 | 0 |

Trajectory categories (exhaustive, mutually exclusive):

- repaired_by_final_level: 1725
- wrong_at_every_level: 275

| Transition | Wrong → wrong | Wrong → right | Right → wrong | Right → right |
|---|---:|---:|---:|---:|
| 1 → 2 | 2000 | 0 | 0 | 0 |
| 2 → 3 | 2000 | 0 | 0 | 0 |
| 3 → 4 | 2000 | 0 | 0 | 0 |
| 4 → 5 | 2000 | 0 | 0 | 0 |
| 5 → 6 | 2000 | 0 | 0 | 0 |
| 6 → 7 | 2000 | 0 | 0 | 0 |
| 7 → 8 | 2000 | 0 | 0 | 0 |
| 8 → 9 | 2000 | 0 | 0 | 0 |
| 9 → 10 | 2000 | 0 | 0 | 0 |
| 10 → 11 | 2000 | 0 | 0 | 0 |
| 11 → 12 | 275 | 1725 | 0 | 0 |

![Measured current correctness](../figures/20261021T015216719695Z-collection-correctness.png)

Exact baseline command, artifact/data digests, upstream SHA, environment and batch costs are recorded in the linked collection/baseline manifests. Outcomes are eventual correctness labels; current incorrect states may self-correct.

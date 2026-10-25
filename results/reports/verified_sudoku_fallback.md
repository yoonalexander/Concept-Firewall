# Practical alternative: verified Sudoku completion

Both prespecified neural retry methods failed to establish a confidence-allocation advantage. As the authorized practical alternative, the project now provides `verified_completion` and the `solve` command: accept a proposed answer only when exact Sudoku verification passes; otherwise solve from the original clues using deterministic minimum-remaining-values backtracking.

This is a classical exact constraint solver baseline. It does not use the confidence probe, train a model, resume the NCM hierarchy, or establish the original learned-monitor research claim. It improves task reliability where exact Sudoku constraints are available; no NLP or general AI safety claim follows.

## Implemented behavior

- Preserve a valid proposed completion without search.
- Reject malformed, incomplete, conflicting or clue-changing proposed completions and solve from the original puzzle.
- Independently verify a completed grid before returning it.
- Return an explicit invalid-input, unsatisfiable or budget-exhausted result with no board when a valid completion cannot be established.
- Bound search by a default 100,000 nodes. The API and CLI require only the Python standard library and existing verifier; no Torch, NumPy or GPU is imported.

## Development validation

The validation reused the 6,400 previously exposed V2 training/validation/calibration puzzles and their retained original final boards. It did not access confirmation, generate new model answers, change any study gate, or fit anything.

| Measurement | Result |
|---|---:|
| Original verified model answers preserved | 2,479 |
| Failed original answers completed by exact solver | 3,921 |
| Combined verified completions | **6,400/6,400** |
| Exhausted or unsatisfiable cases in this cohort | 0 |
| Total fallback search nodes | 1,008,960 |
| CPU validation wall time | 5.83 seconds |
| New model calls / fits | 0 / 0 |

Every resulting board passed a second, independent constraint implementation. The 5.83-second measurement includes CPU fallback, verification and host audit/record assembly; it excludes the already completed NCM generation. It is not an end-to-end NCM speedup or a population-wide 100% guarantee. Arbitrary inputs may be inconsistent or exhaust the explicit search cap. Full retained data, source hashes and timing scope are in [verified_fallback.json](../continuation/verified_fallback.json).

## Use

```powershell
.venv\Scripts\python.exe -m concept_firewall solve --puzzle '530070000600195000098000060800060003400803001700020006060000280000419005000080079'
```

Add `--board 'MODEL-OUTPUT'` to verify a proposed completion first, or `--node-limit 1000` to lower the search allowance. The command prints structured JSON and exits 0 only for a verified completion; it exits 1 for an unresolved/invalid puzzle and 2 for invalid command/configuration values. Python callers use `concept_firewall.verified_solver.verified_completion` with the same semantics.

The independent [artifact audit](../continuation/audit.json) checks all 6,400 fallback boards and preserves every already correct model answer. This practical baseline completes the available Sudoku reliability alternative; it does not reopen the failed frozen studies.

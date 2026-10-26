# Concept Firewall CLI 0.2.0

Verify a 9x9 Sudoku completion, or preserve a valid proposed answer and fall back
to bounded exact solving. Python 3.10+; no runtime dependencies, model, Torch,
CUDA, datasets, network access or submodule needed for `verify` and `solve`.

This is a classical Sudoku utility. The closed research studies found that
confidence warnings identified failures but did not improve retry allocation
under the tested policies. Exact solving is **not a successful learned firewall**
or a general AI safety guarantee. The historical `sudoku-study-v0.1.1` release
and its notes remain unchanged.

## Install

Download the wheel and `SHA256SUMS` from the GitHub CLI release. Compare its
SHA-256 with the corresponding line (`Get-FileHash` in PowerShell, or
`sha256sum` on Linux). In a new environment:

```console
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\python.exe -m pip install --no-index ./concept_firewall-0.2.0-py3-none-any.whl
.venv\Scripts\concept-firewall.exe --version
# macOS/Linux equivalents:
.venv/bin/python -m pip install --no-index ./concept_firewall-0.2.0-py3-none-any.whl
.venv/bin/concept-firewall --version
```

Use the command for your platform. After activating the environment,
`concept-firewall` and `python -m concept_firewall` are equivalent. This release
is distributed through GitHub, not PyPI. To install the source distribution:

```console
python -m pip install ./concept_firewall-0.2.0.tar.gz
```

Source installation needs the build dependency `setuptools>=68`; pip may fetch
it from its configured index. Offline, use `--no-index --find-links WHEELHOUSE`
with a predownloaded setuptools wheel. Neither installation needs research
extras. Legacy research commands remain available for compatibility but require
the full repository, configs, upstream source and appropriate extras; they are
outside this CLI release's standalone support.

## Use

```console
concept-firewall solve --puzzle 530070000600195000098000060800060003400803001700020006060000280000419005000080079
concept-firewall verify --puzzle 530070000600195000098000060800060003400803001700020006060000280000419005000080079 --board 534678912672195348198342567859761423426853791713924856961537284287419635345286179
concept-firewall solve --puzzle 530070000600195000098000060800060003400803001700020006060000280000419005000080079 --board bad-proposal --node-limit 100000
```

Inputs contain exactly 81 ASCII cells, optionally with ASCII whitespace, or nine
9-cell rows separated by `|` (quote these on the command line). `0`, `.`, `_`
mean blank. Prose, Markdown fences, commas and Unicode lookalikes are rejected.
`verify` requires a complete board. `solve` checks the puzzle first; an incorrect,
incomplete or malformed optional proposal triggers solving from the original
clues. It never treats a proposal as extra clues.

Run `python examples/sudoku_demo.py` from the extracted source distribution or
repository after installation. The demo invokes both installed entry points,
shows a rejected proposal and repaired solution, and exits nonzero on failure.

## JSON output and exit codes

Both commands emit a JSON object on stdout, including unsuccessful outcomes.
Usage/configuration errors emit diagnostics on stderr instead.

`verify` fields:

| Field | Meaning |
| --- | --- |
| `is_valid` | Complete, respects all original clues, and every row/column/box contains 1-9. |
| `is_complete`, `filled_cells` | Whether the parsed output has all 81 cells filled, and the number filled. |
| `malformed` | The proposed output could not be parsed; does not describe puzzle validity. |
| `clue_violations` | Number of original nonblank clues changed or omitted. |
| `row_conflicts`, `column_conflicts`, `box_conflicts` | Duplicate occurrences beyond the first, summed over units; blanks excluded. |
| `errors` | Diagnostic strings; `invalid_puzzle:` identifies malformed/conflicting original clues. |
| `board` | Parsed output as 81 integers (0 for blanks), or `null` on parse failure. This can be present even when invalid. |

`solve` fields:

| Field | Meaning |
| --- | --- |
| `status` | `accepted_proposal`, `solved_exact`, `invalid_puzzle`, `unsatisfiable`, or `budget_exhausted`. |
| `board` | Verified completion as an 81-digit string; `null` for every unsuccessful solve. |
| `verified` | True only for a verified completion. |
| `used_fallback` | True if exact search was attempted (including unsuccessful search). |
| `search_nodes` | Recursive search calls visited, including the root and any completed leaf; at most the node limit. |
| `reason` | Human-readable explanation; use `status` for programmatic decisions. |

| Exit | Meaning |
| --- | --- |
| `0` | Valid completion (`verify`) or verified result (`solve`). Also help/version. |
| `1` | Verification rejected; or solve returned invalid puzzle, unsatisfiable, or budget exhausted. Malformed puzzle/board text also uses this structured failure path. |
| `2` | Invalid command/arguments, missing required flags, invalid/nonpositive node limit, or caught runtime/environment error. |

## Limits

Only ordinary 9x9 Sudoku is supported. Deterministic minimum-remaining-values
backtracking returns the first valid completion; it does not prove uniqueness
or use a learned model. The default budget is 100,000 search nodes, a work bound
rather than a wall-clock timeout. `--node-limit` must be a positive integer.
An already valid proposal needs zero search nodes. Conflicting clues are an
`invalid_puzzle`; a consistent-looking grid with no possible completion is
`unsatisfiable` only after exhaustive search. `budget_exhausted` does **not**
prove unsatisfiability. No partial answer is returned by an unsuccessful solve.

The original project code has no project-wide license grant; see
`THIRD_PARTY_NOTICES.md`. This release does not choose a new license.

# CLI 0.2.0 tested delivery

Release branch: `codex/cli-release`, forked from `main` at
`a5ea81eb1e3e6085473b69cb7944a571bdee8794`. Packaging/documentation phase:
`11fa3579d443772478b86624e12e80f0a40eb948`. Build/verification phase:
`162575ef2e432cd186569b1cfef0783b63873427`.

The wheel and sdist were built from the package sources committed by those two
phases. The final delivery phase adds only this record and checksums. The GitHub
draft `cli-v0.2.0` targets the delivery commit on this branch; main is not merged
or moved. Historical `RELEASE_NOTES.md` and the `sudoku-study-v0.1.1` tag
(`e81de0a98fa55b0dbd5b59fd6703adce7a078b5d`) remain unchanged.

## Acceptance evidence

[Machine-readable verification](cli-release-verification.json) records exact
asset hashes, archive inventories, packaging-tool versions, installed packages
and every successful command check:

- Both the wheel and sdist installed offline in separate clean environments on
  Windows with Python **3.12.10** and **3.14.2**: **4 clean installations**.
- **82 checks per environment, 328 total**, exercise both installed console and
  module entry points. Valid answers, incorrect/changed-clue proposals, incomplete
  and malformed text, conflicting clues, consistent-but-unsatisfiable puzzles,
  and exhausted search budgets all satisfy the documented output/exit contract.
- Every environment ran the runnable demo and `pip check`; research packages,
  Torch, CUDA packages and ML imports were absent. Each successful completion
  passed a separate clue/row/column/box checker.
- **26 adversarial parser/verifier unit tests** extracted from the sdist passed
  against the final installed environment. The **31 existing verifier/solver
  tests** also passed from source without research dependencies.
- Additional compatibility check: **121 repository regression tests passed**
  using the existing research venv and original checkout's pinned upstream source,
  with `PYTHONPATH` pointing at this release worktree's changed package. The bare
  release worktree intentionally has no upstream submodule. Those research tests
  require optional dependencies/upstream files and are not the clean-install
  acceptance suite. No study or real model generation was rerun.
- The allowlist inspected every wheel/sdist member and confirmed identical
  Python modules. No checkpoints, datasets, raw evidence, submodules, local
  environments or retained-evidence archives are attached.

The first Python 3.14 sdist installation exceeded Windows' path limit under this
deeply nested worktree. Repeating the acceptance run with a shorter writable
temporary path passed all four combinations. See [build instructions](../../docs/cli_release.md).

The CI workflow independently checks rebuilt distributions on Windows/Linux
with Python 3.10, 3.12 and 3.14. CI rebuilds are distinct from the exact local
assets identified by this checksum manifest; do not substitute CI builds without
retesting and regenerating checksums.

## Assets and use

The draft contains exactly the wheel, sdist, `CLI_README.md`,
`CLI_RELEASE_NOTES.md`, `cli-release-verification.json`, and `SHA256SUMS`.
[SHA256SUMS](SHA256SUMS) covers the other five files. Uploaded asset bytes are
downloaded and compared with the local originals as the final delivery check.
The tested archives are kept in this worktree's ignored `dist/` directory.
GitHub's automatic repository source snapshots are not the tested sdist.

Install the downloaded wheel with:

```console
python -m pip install --no-index ./concept_firewall-0.2.0-py3-none-any.whl
python -m concept_firewall --version
```

See [CLI instructions](../../CLI_README.md), [demo](../../examples/sudoku_demo.py),
and [release notes](../../CLI_RELEASE_NOTES.md). No PyPI publication or paid
services are part of this delivery. The research findings remain closed and
negative for tested retry-allocation benefit; exact solving is a classical
fallback and does not validate a learned firewall.

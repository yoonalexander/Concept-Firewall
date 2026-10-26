# Integrated CLI 0.2.0 delivery

PR #1 packages the dependency-free verifier and bounded exact fallback. PR #2
adds the completed exposed-data recoverability analysis, with its inconclusive
evidence/no-go conclusion preserved. Both PRs are integrated into `main`.

## Reviewed integration

- PR #1 head: `f099075c18c920993ee481787b3c95785ac0a63e`; merge commit
  `17c1e04fdc37b482c80498280b0c19ce47ac82b0`.
- PR #2 head: `0ba466f98d88eec8987d8a5d6502f49383db12ab`; merge commit
  `9912d4e7d3555689f278d18d6d0d5355f2615dab`.
- Combined regression: **128 tests and 133 subtests passed**, plus `pip check`.
- In an extracted committed source copy, no-fit audits independently checked
  1,600 original outcomes, 3,200 retries, 6,400 exact-fallback outcomes, all 60
  recoverability allocation/budget points, training-only means and protected
  artifact/ledger hashes. No consumed experiment was rerun.

[Integration verification](integration-verification.json) records those checks.
The earlier PR #1 branch-only draft report and checksums are retained under
[pr1-draft/](pr1-draft/README.md); they do not identify the integrated release
assets. No historical research result, source snapshot, consumed ledger or
`sudoku-study-v0.1.1` tag was replaced.

## Final release assets

The release process builds both distributions from a clean Git archive of the
exact committed `main` revision selected for `cli-v0.2.0`. It rechecks archive
allowlists, matching Python sources and clean offline installations of both
wheel and sdist on Python 3.12 and 3.14. CI additionally checks Windows/Linux
on Python 3.10, 3.12 and 3.14.

The authoritative final asset hashes, exact build commit and measured clean
installation results are published as release assets, outside the source tree
being built. This avoids recording a source revision or checksum that refers
to a different build. Obtain them from the
[CLI 0.2.0 release](https://github.com/yoonalexander/Concept-Firewall/releases/tag/cli-v0.2.0):

- `concept_firewall-0.2.0-py3-none-any.whl`
- `concept_firewall-0.2.0.tar.gz`
- `CLI_README.md`
- `CLI_RELEASE_NOTES.md`
- `cli-release-verification.json`
- `integration-verification.json`
- `SHA256SUMS` (covers the other six assets)

The final release is published only after uploaded bytes match the tested local
files and the selected source commit's six CI jobs pass. The tag targets that
exact tested commit. Download files and verify `SHA256SUMS` before installing.
GitHub's automatic repository snapshots are not the tested source distribution.
No checkpoints, datasets, raw evidence or Python environments are attached.

```console
python -m pip install --no-index ./concept_firewall-0.2.0-py3-none-any.whl
python -m concept_firewall --version
```

See [CLI instructions](../../CLI_README.md), [demo](../../examples/sudoku_demo.py),
[release notes](../../CLI_RELEASE_NOTES.md) and
[build instructions](../../docs/cli_release.md). No PyPI publication is included.
Exact constraint solving is a classical Sudoku fallback and does not establish
a successful learned firewall or general AI safety effectiveness.

# CLI 0.2.0

This release packages the dependency-free Sudoku verifier and bounded exact
fallback already present at research closeout `a5ea81e`. It adds standalone
installation/use documentation, a runnable installed-command demo, version
reporting, an explicit source archive allowlist, and distribution-level checks.

- `verify` accepts exactly complete answers that preserve original clues and
  satisfy all row, column and box constraints.
- `solve` preserves a valid proposal or runs deterministic bounded exact search
  from original clues. Invalid, unsatisfiable and exhausted outcomes return no
  board; no unchecked partial result is returned.
- Wheel and source distribution have no runtime requirements. Research extras
  remain opt-in for historical checkout workflows.
- Distribution assets exclude checkpoints, datasets, raw research evidence,
  retained-evidence archives, upstream submodules and local environments.
- The default 100,000-node budget is not a timeout or a uniqueness proof.

The research studies remain closed: confidence warnings identified failures
but did not improve retry allocation under the tested policies. This exact
solver is a classical engineering fallback, not a successful learned firewall.
No research gate is reopened or upgraded by the `0.2.0` version number.

The historical `0.1.1` study release, `sudoku-study-v0.1.1` tag and
`RELEASE_NOTES.md` are preserved. No PyPI publication or model runs are included.

Release assets: `concept_firewall-0.2.0-py3-none-any.whl`,
`concept_firewall-0.2.0.tar.gz`, `SHA256SUMS`, `cli-release-verification.json`,
`CLI_README.md`, and these notes. The verification JSON records the exact tested
asset hashes, Python/platform/tool versions, archive inspection and clean
environment checks; checksums cover all companion assets except `SHA256SUMS`
itself. Build and verification instructions are in `docs/cli_release.md` in the
repository. GitHub may also offer automatic repository source snapshots; those
are not the tested source distribution.

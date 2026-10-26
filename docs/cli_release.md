# Building and testing the CLI release

Use a clean checkout of `codex/cli-release`. No research data, upstream submodule,
CUDA or model dependencies are needed. Run from the project root with Python
3.10+ (commands below assume the build environment is activated):

```console
python -m venv .tmp/build-env
# Activate .tmp/build-env with your platform's usual command.
python -m pip install build "setuptools>=68" wheel
python -m build --no-isolation
python -m pip download --no-deps --dest .tmp/wheelhouse "setuptools>=68"
python scripts/verify_cli_release.py --wheelhouse .tmp/wheelhouse --python python
```

`build` creates the source distribution first, then builds the wheel from that
source archive. `--no-isolation` uses only the explicit build tools above; the
test installer still builds the sdist in pip's isolated build environment using
only the offline setuptools wheelhouse. Pass multiple `--python` paths to check
several installed Python versions. Keep `TEMP`/`TMP` on a writable path if local
Windows restrictions prevent `venv`/`ensurepip` from using the default temp area.
For deeply nested Windows checkouts, pass `--work-dir` pointing to a short,
writable temporary directory. Pip's isolated source build can otherwise exceed
the Windows path limit (observed with Python 3.14); this is an installer path
limit, not a solver failure.

The standard-library verification script:

1. Inspects every archive member against a release allowlist and checks wheel
   metadata, version, entry point, optional-only requirements, and identical
   Python sources in the wheel and sdist.
2. Creates separate fresh virtual environments for each artifact/interpreter,
   with no system site packages and no `PYTHONPATH`/`PYTHONHOME` influence.
3. Installs the wheel offline and the sdist through an isolated offline build;
   runs all commands in a directory outside the source package.
4. Tests the console script and `python -I -m concept_firewall`, including valid
   answers, changed clues, duplicate digits, incomplete/malformed inputs,
   Unicode lookalikes, alternate valid completions, optional-proposal fallback,
   conflicting clues, unsatisfiability, budget exhaustion, and argument errors.
   Successful boards also pass a separate row/column/box/clue checker.
5. Asserts research packages and CUDA distributions are absent, checks no ML
   imports on the solve path, runs the demo and `pip check` in every environment,
   and runs the 26 existing adversarial parser/verifier tests from the sdist.
6. Writes `dist/cli-release-verification.json` with hashes and check details.

The GitHub workflow performs the same build and installation checks on Windows
and Linux with Python 3.10, 3.12 and 3.14. Workflow artifacts are CI output, not
automatic releases; the workflow never publishes to GitHub releases or PyPI.

## Delivery

Copy `CLI_README.md` and `CLI_RELEASE_NOTES.md` beside the two distributions and
verification report. Generate `SHA256SUMS` over precisely those five files. Keep
the binaries in ignored `dist/`; commit the verification report and checksum
manifest under `release/0.2.0/` for review. A GitHub draft release must attach
exactly these tested files plus `SHA256SUMS`, target the reviewed release-branch
commit, and preserve the `sudoku-study-v0.1.1` tag. Download each uploaded asset
and compare its bytes/SHA-256 before reporting delivery. GitHub's automatic
repository snapshots are separate from the tested `.tar.gz` source distribution.

No checkpoints, datasets or raw research evidence may be included in the tested
archives or attached assets. Do not publish to PyPI, merge the PR, or move main.

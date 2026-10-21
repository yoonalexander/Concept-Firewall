# Reproduction log

Initial implementation on October 20, 2026 (America/Toronto). This log will be updated with exact run manifests after execution.

Source pinned: `c70274273f489abc73832b2b98584a8483b6b203`. Local upstream source remains unmodified. Host has NVIDIA RTX 5060, 8 GB, driver 610.88; the default system Python 3.14 had CPU-only PyTorch 2.11.0, so a separate Python 3.12 environment was created for CUDA. Initial sandbox temporary-directory ACL errors were resolved by pointing TEMP/TMP into the ignored project `.tmp` directory.

The supplied artifact wildcard paths were corrected after inspecting Hub listings: `sudoku/hard/*` remotely, `sudoku-hard/` locally. Exact revisions and digests are recorded in `results/manifests/artifacts.json`. No paid compute or service was used.

All implementation/evaluation commands and outcomes must be recorded below or in linked manifests before being described as passed.

## Recorded execution

- The CUDA environment preflight passed: Python 3.12.10, PyTorch 2.11.0+cu128, CUDA runtime 12.8, RTX 5060. The isolated environment passes `pip check`; `requirements.lock` records its packages and explicitly identifies itself as an environment snapshot.
- Official smoke: `20261021T014201396770Z-baseline`, 24/32 reference-equal solutions. Official full set: `20261021T014335328137Z-baseline`, 1,725/2,000 reference-equal solutions, 98.36% cell accuracy, 86.25% valid grids. Exact commands, versions, hashes and raw directories are in the respective `results/manifests/` JSON files.
- Initial direct decoding of short `z_levels` did not produce full candidate boards. The report `results/reports/reconstruction_correction.md` records this implementation finding and supersedes the initial two collection runs and initial probe run. No metrics from the initial probe run were used to select the revised protocol; levels/models/splits stayed fixed.
- Corrected collection: `20261021T015216719695Z-collection`, 2,000 unique puzzles × 12 levels = 24,000 observations, every final output equal to the official baseline. The feature contract is `sudoku-full-prefix-v2`; source snapshot `2ac472dc63e2ec4c845b0059fc014a2cfc18a37423519a35ee6ea536f66f0d5b` is preserved. Full-length accumulator snapshots use the upstream quantizer API and are cloned before later levels mutate the accumulator.
- Verification after correction: **74 tests and 119 subtests passed**, including actual upstream tiny-model strict checkpoint loading, full prefix length/storage independence, future mutation independence, Sudoku adversarial cases, immutable/strict storage, grouped splits, probability metrics, and portable probe arithmetic. Command: `.\.venv\Scripts\python.exe -m pytest -q` with TEMP/TMP set to the ignored project `.tmp` for this sandbox.
- No upstream source patches, paid compute, hosted service, branching, online intervention or frontend were introduced. Work continued independently after all subagents became inactive.
- Corrected probe evaluation: `20261021T015457393177Z-probes`, 1,000/300/300/400 grouped train/validation/calibration/test puzzles. Primary level-6 incremental AUROC −0.00779115; 500 paired puzzle-bootstrap replicates give 95% interval [−0.03679288, +0.01926330]. No demonstrated latent gain. Full metrics/parameters/thresholds and all levels are recorded in the run manifest and report; no test-driven retuning was performed.
- Artifact audit: `20261021T015457393177Z-probes-artifact_validation.json` passed. Five saved level-6 probe families each reproduced all 400 held-out probabilities within 1e-12 after loading portable JSON; their stored scaler means match training-only vectors. Frozen split hashes and model/script digests are retained. Research source snapshot `ecd2d222eeff7ad6715c671b48c9d63ace6c7ed8d228b2c4d3c3e167b7122783` is preserved in the run manifest.
- The result is a valid negative initial experiment. Work stops at the M3 gate; the implementation does not advance to custom branching, live intervention or UI.

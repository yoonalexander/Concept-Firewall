# Reproduce the scoped Sudoku study

Package version **0.1.1** preserves the negative M0–M3 study. M4–M7 remain deferred. The tested environment is Windows, Python 3.12.10, CUDA 12.8, and an RTX 5060. Other platforms are not covered by this reproduction check.

## 1. Clean source and isolated dependencies

```powershell
git clone --recurse-submodules https://github.com/yoonalexander/Concept-Firewall.git
cd Concept-Firewall
git checkout sudoku-study-v0.1.1
git submodule update --init third_party/ncm
py -3.12 -m venv .venv
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP = (Resolve-Path .tmp).Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pip install -r requirements.lock --extra-index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m concept_firewall doctor
.\.venv\Scripts\python.exe -m pytest -q
```

The dependency snapshot is specific to the recorded machine and Python version. This setup installs a roughly 2.75 GB CUDA PyTorch wheel; the research artifact download below is separate. It is not a portable, hash-locked dependency resolution. The tag identifies this scoped package, not the design's v1.0 milestone.

## 2. Restore retained evidence and official artifacts

Obtain `sudoku-study-artifacts.zip` from the delivered `dist` folder (about 186 MB decimal), separately from the Git repository. It is a local delivery artifact; there is no automatic public download URL for it. The committed [inventory](../results/manifests/sudoku_study_artifacts.json) lists every retained file and the exact archive digest.

```powershell
.\.venv\Scripts\python.exe scripts/study_artifacts.py restore --archive C:\path\to\sudoku-study-artifacts.zip
.\.venv\Scripts\python.exe -m concept_firewall download
```

Restore verifies the archive and all 174 member digests before writing. It refuses conflicting existing content. The archive contains corrected trajectories, fitted probes, follow-up features/models, and retained evaluator outputs; intentionally superseded trajectories/probes remain on the original research machine. Historical manifests and source snapshots for the superseded runs remain in Git. The four official checkpoint/dataset files are downloaded from immutable revisions and hash-checked (about 164 MB decimal).

To rebuild the ZIP on a machine retaining the original evidence:

```powershell
.\.venv\Scripts\python.exe scripts/study_artifacts.py pack --archive dist/sudoku-study-artifacts.zip --inventory .tmp/rebuilt-artifacts.json
```

Compare the newly generated inventory with the committed inventory before using it. Do not replace historical evidence with regenerated output under the old run IDs.

## 3. Replay the checks and fixed follow-up

```powershell
.\.venv\Scripts\python.exe scripts/verify_probe_artifacts.py --manifest results/manifests/20261021T015457393177Z-probes.json --output .tmp/replayed-probes.json
.\.venv\Scripts\python.exe -m concept_firewall audit --protocol configs/m3_followup.json
# Substitute the newly printed audit manifest:
.\.venv\Scripts\python.exe -m concept_firewall followup --audit-manifest results/manifests/NEW-m3-audit.json --protocol configs/m3_followup.json
```

The portable-probe audit checks all 400 held-out predictions for five primary-level families and their training-only scaler means. The independent audit checks all 24,000 retained labels and 2,000 final outputs. The final command reconstructs only the declared development prefixes from retained codes, fits the same frozen comparisons, and records a new run. Compare metrics, folds, projection hashes, and conclusions; timestamps, execution paths, ZIP metadata, timings, and compressed NPZ bytes need not be identical.

This is **retained-evidence replay**, not a second full baseline or collection run and not fresh confirmation data. It deliberately avoids full model generation and selecting additional models. Original raw evidence is preserved; new audit/follow-up outputs use new run IDs. Do not invoke the old artifact-verification script without `--output` when preserving its historical validation manifest.

## 4. Optional full regeneration

The [README](../README.md) documents full baseline, collection, analysis, and probe commands using `configs/sudoku_probe.yaml`. Those commands generate new run IDs; keep their outputs separate and pass each newly printed manifest into the next command. The frozen follow-up configuration refers to retained original run IDs. A full regenerated study needs a separately named copy of that configuration pointing to the new collection, probes, and splits; it must not rewrite the historical protocol or claim to recover old artifact bytes.

Full generation was not repeated for this delivery. Source snapshots preserve the exact experimental code used for the original results. Cross-hardware determinism, a fresh dataset, and independent scientific replication remain outside the verified scope.

## Package boundaries

The source ZIP includes the pinned NCM source and its MIT license, but no Git metadata. Use the tagged Git checkout above for commands that require upstream revision verification. The wheel installs the Python CLI; model commands also need the complete checkout, configs, submodule, and artifacts. Dependencies and weights are not bundled. Consult [release notes](../RELEASE_NOTES.md) and [notices](../THIRD_PARTY_NOTICES.md) before distributing the package.

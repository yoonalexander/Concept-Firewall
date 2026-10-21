# Official hard-Sudoku evaluation

On October 20, 2026 (America/Toronto), the unmodified upstream evaluator completed:

| Run | Inputs | Reference-equal solved | Valid grids | Cell accuracy |
|---|---:|---:|---:|---:|
| Smoke | 32 | 24 (75.00%) | 75.00% | 97.26% |
| Full released test set | 2,000 | 1,725 (86.25%) | 86.25% | 98.36% |

These are locally measured results of the released evaluator, not a claim of matching a paper's full hardware/software protocol. The wrapper's stricter clue-preserving validator also accepted exactly 1,725/2,000 final outputs.

- [Smoke manifest](../manifests/20261021T014201396770Z-baseline.json)
- [Full manifest](../manifests/20261021T014335328137Z-baseline.json)
- [Pinned artifact revisions and SHA-256 digests](../manifests/artifacts.json)
- [Corrected observational manifest](../manifests/20261021T015216719695Z-collection.json)

Exact command (from project root):

```powershell
.\.venv\Scripts\python.exe -m concept_firewall baseline --config configs/sudoku_probe.yaml
```

The manifest records the underlying official `evaluate.py` command, full stdout, exact artifact hashes, upstream SHA, config, environment and raw log directory. Raw outputs/logs remain under ignored `results/raw/`; each output used for collection was compared by puzzle row. The tokenizer and generator loaded with strict state-dict checks.

Source: unmodified NCM `c70274273f489abc73832b2b98584a8483b6b203`, MIT. Python 3.12.10, PyTorch 2.11.0+cu128, CUDA runtime 12.8, NVIDIA RTX 5060 (8 GB), driver 610.88, Windows 11. Documented deviations: one GPU and batch size 8 instead of the released batch size 128. Deterministic temperature 0.0, top-k 0, top-p 1.0, guidance 0.0. The official CLI does not expose a seed flag; no stochastic-branch reproducibility is claimed.

The upstream solved metric compares the supplied reference; grid validity does not enforce original clues. Our final-valid label checks exact format, completeness, every clue, rows, columns and boxes and accepts alternative valid solutions. These are distinct definitions even though the counts agree here.

Native short `z_levels` were initially decoded incorrectly for the intended intermediate-board analysis. Those observations/probes are superseded; the official baseline and final equivalence remain valid. See [correction](reconstruction_correction.md).

# Reproduce the saved recoverability analysis

Read `results/reports/recoverability_analysis.md` and the frozen `configs/recoverability_analysis.json` first. This is exposed-data exploration. Existing failed gates and consumed ledgers remain closed.

## Evidence

The committed `results/recoverability/` directory contains the inventory, separate research ledger, all OOF predictions, full metrics, an independent audit, and byte hashes. `.gitattributes` preserves those evidence bytes and the executed analysis source bytes across operating systems. The source implementation was committed as `f58300e` before the real fits; the final branch preserves its actual executed Windows bytes as well as the same program text.

Ignored raw source files remain in the original checkout. Its three paired JSONL tables are named in `inventory.json` and checked against the earlier evidence inventory. For another computer, use the existing confidence-allocation evidence ZIP and restoration instructions in `docs/reproduce_confidence_allocation.md`. Restore into a separate source-data directory, and verify the old archive hash. Do not replace or reset any consumed ledgers. No checkpoints, upstream submodule, model download, CUDA or model outputs are needed for this analysis.

Dependencies used: Python 3.12 (see exact version in results.json), NumPy 2.5.4, scikit-learn 1.9.1, and their existing SciPy/threadpoolctl dependencies. The existing source-checkout `.venv` was reused; there was no paid compute or dependency installation. The script prepends this worktree's `src` so the editable environment cannot silently import the source checkout's implementation instead.

## No-fit audit

From the analysis worktree, use the existing Python environment:

```powershell
& C:\Users\Admin\Documents\Projects\Concept-Firewall\.venv\Scripts\python.exe scripts/audit_recoverability.py --source-root C:\Users\Admin\Documents\Projects\Concept-Firewall
```

The audit verifies all protected hashes, both independently checked recovery targets, group fold assignments, training-only scaler means, 60 policy/budget allocation counts, service slots and historical confidence rescues. It makes zero fits and never imports the upstream generator. It writes an audit sidecar; use a separate copy if preserving the originally recorded audit timing bytes. The audit is not an independent statistical confirmation.

Focused tests are `tests/test_recoverability_analysis.py`, `tests/test_no_future_leakage.py`, and `tests/test_group_splitting.py`. Point `PYTHONPATH` to this worktree's `src`; use workspace-local TEMP/TMP on Windows if needed. Synthetic test classifiers return constants, with no research estimator fitting.

## Original bounded run

The executed scientific command was:

```powershell
& C:\Users\Admin\Documents\Projects\Concept-Firewall\.venv\Scripts\python.exe scripts/analyze_recoverability.py --source-root C:\Users\Admin\Documents\Projects\Concept-Firewall
```

The separate ledger now records completed status and intentionally refuses to run again. Do not delete it to obtain another attempt. Reproduction with new fits would require a separately authorized disposable replay copy and a separate ledger; it would still reuse exposed development data and could not become confirmation. Auditing the committed OOF predictions needs no additional fitting.

The 40-fit and 600-process-CPU/1,200-wall-second watchdog bounds cover the scientific analysis body, including data audit, fitting, bootstrap and output serialization. Timings exclude interpreter/import startup and ancillary tests/report assembly, reported separately in the report. Attempted fits are durably charged before estimator construction; errors retain the charge. The watchdog terminates at the resource limit, and the ledger blocks reruns. No all-data deployment model is fitted or exported.

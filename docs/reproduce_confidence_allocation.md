# Reproduce the confidence allocation evidence

This guide replays the retained, separately registered `confidence-allocation-v1` evidence without fitting or GPU inference. It does not rerun confirmation or provide a new independent test. The historical V2 study remains failed and closed.

## Source and environment

Use a checkout containing [the follow-on roadmap](../ROADMAP_CONFIDENCE_ALLOCATION.md), [protocol](../configs/confidence_allocation.json), frozen probe/contract, small result JSON files, executed source ZIPs and the audit scripts. The artifact audit needs NumPy and SciPy in the existing research environment. Follow the main README for that environment. No official checkpoint is needed for retained-data audit; do not load unreviewed checkpoint or pickle files.

The confirmation and recovery manifests preserve the exact scientific source ZIP executed, including uncommitted source at run start. Their shared provenance helper initially recorded module-style commands even though the actual invocation used `scripts/confidence_allocation.py confirm` / `recover`. [The audit sidecar](../results/continuation/audit.json) records the correction and hashes without changing historical manifests. Later source corrects command recording for future use. There were no scientific reruns for this metadata issue.

## Retained evidence archive

Local archive: `dist/confidence-allocation-v1-evidence.zip`. The committed [inventory](../results/continuation/evidence_inventory.json) records its SHA-256, size and every member digest. The ZIP is a local artifact, not a GitHub Release upload. Obtain this exact archive from the originating workspace when moving machines. Git contains the small results, source and inventory, while the raw tables remain ignored.

The seven-file bundle contains the complete confirmation inputs/current features/final boards/codes/scores, every fixed-prefix and full-restart potential retry outcome, all practical exact-fallback results and their original audited development inputs/outcomes, the consumed follow-on ledger, and the unchanged old V2 ledger needed to check the frozen contract. It includes no checkpoint or Python environment. Preserve counters and all failed-attempt records; do not reset a ledger to repeat a consumed experiment.

From a source checkout:

```powershell
.venv\Scripts\python.exe scripts/confidence_allocation_evidence.py restore --archive PATH-TO-ZIP
.venv\Scripts\python.exe scripts/audit_confidence_allocation.py
```

The restore command checks the archive and all members before writing. It refuses conflicting existing files and preserves them. Restoring again verifies identical files rather than overwriting them. The independent audit checks every outcome with a separate Sudoku constraint implementation, frozen puzzle/group order, input identities, decision-time board features, all frozen probe alerts, retry seeds, forced-prefix preservation, expected and realized baseline counts, service envelopes and budget limits. It also independently validates all 6,400 practical fallback boards and preservation of the 2,479 originally valid answers. It makes zero model calls and zero fits.

The [replay verification](../results/continuation/replay_verification.json) records the clean-source restore/audit result and its exact environment boundary. Reusing the existing dependency environment for a clean-source audit is not a clean-environment model reproduction or a completion claim for V2-8.

To repeat the source/evidence restoration check, run `.venv\Scripts\python.exe scripts/verify_allocation_replay.py`. It uses a new folder under `.tmp`, restores the archive twice, proves imports come from the extracted committed source, and audits all 11,200 retained outcomes. The recorded check used scientific source commit `139e066`, plus the explicitly hashed closeout helper and inventory. It does not modify original raw evidence or ledgers.

## Original scientific commands and stopping rules

The original sequence was:

```powershell
.venv\Scripts\python.exe scripts/check_confidence_value.py
.venv\Scripts\python.exe scripts/confidence_allocation.py freeze
# Protocol/contract committed and pushed before confirmation outcomes.
.venv\Scripts\python.exe scripts/confidence_allocation.py confirm
# Confirmation result committed and pushed before recovery.
.venv\Scripts\python.exe scripts/confidence_allocation.py recover
.venv\Scripts\python.exe scripts/audit_confidence_allocation.py
.venv\Scripts\python.exe scripts/report_confidence_allocation.py
```

The confirmation/recovery commands intentionally reject repeated attempts and changed frozen artifacts. They are documentation of a consumed experiment, not instructions to open the old V2 gate or rerun until success. A new scientific question needs a separate prospective plan and fresh evidence; the now-exposed confirmation set cannot be relabeled as untouched.

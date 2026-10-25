# V2-1: generator observation validation

**Decision:** pass for bounded observation and generation equivalence. No detector was fitted, and no predictive benefit is claimed.

The [frozen protocol](../../configs/v2_study.json) observes the normalized transformer input to the level-6 head. An ordinary forward hook captures the current hidden representation and logits. A temporary wrapper delegates to the unchanged upstream sampler and exports an immutable current-prefix snapshot immediately after current-code selection, before the next level can execute. The upstream source and checkpoint weights are unchanged. Hooks and the temporary wrapper are removed on success or exception; no global RNG is used for the fixed projection.

The [pilot manifest](../manifests/20261025T024909530398Z-v2-pilot.json) records all 128 frozen legacy training identities in batches of 8. Every observed/unobserved full code sequence matched exactly. Every final decoded board matched, every exported current prefix matched the generated prefix, and all 16 boundary callbacks arrived exactly once. These are equivalence checks, not 128 additional correctness successes or a scientific prediction evaluation.

The retained 128 × 256 activation vectors, six confidence summaries per puzzle, and 128 prefixes occupy **134,874 compressed bytes**. Feature SHA-256 is `b60d077e8a860b23e8cb7dff6d84250bc6391d8aca502df5c2e2d171239982f6`; projection SHA-256 is `35756c1a10fe0eee1324a2962c339a2aa2a2b6a7c67be721d8b170555efdcfc0`. The feature path is in the manifest and ignored by Git. The source snapshot preserves the exact pilot implementation; a subsequent preflight check also rejects changed official artifacts before checkpoint loading.

The persistent ledger charged **5.62 seconds** of GPU-assisted synchronized elapsed stages, including checkpoint loading, host work, paired baseline/observed generation, and decoding. This conservative budget charge is not a measured monitoring overhead or live savings result. Pilot allowance is now 128/128; no repeat pilot is authorized under the same allowance. Probe fits and new confirmation puzzles remain zero.

Verification passed **99 tests and 123 subtests**. New actual-upstream tiny-model tests check code/board and Torch RNG equivalence, immutable observations, unchanged early features after a future head mutation, callback ordering before the future head, repeated/batch-order behavior, cleanup after observer failure, confidence arithmetic/non-finite rejection, and artifact verification before loading. No historical result artifacts were overwritten.

Reproduction command: `.venv\Scripts\python.exe -m concept_firewall v2-pilot`. It uses the frozen contract and persistent ledger; rerunning consumes remaining allowances and cannot reset the study. Tests use separate synthetic fixtures and temporary ledgers, not the scientific pilot allowance.

**Next:** V2-2 must audit a new source and freeze data partitions before new-data capture or fitting. If fresh independent project data cannot be justified, only the explicitly exposed legacy feasibility route may advance; confirmation and online/recovery phases remain closed.

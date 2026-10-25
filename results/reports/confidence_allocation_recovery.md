# Confidence allocation: measured recovery

**Decision:** Neither the primary recovery method nor the predeclared alternative established the required confidence-allocation advantage. Close this bounded follow-on.

The fixed warning score passed the separate held-out failure-enrichment screen. This phase asks the harder question: does allocating retries with that warning actually improve verified answers at comparable resources? The original V2 detector study remains closed and failed.

## Fixed execution

The protocol was committed and pushed before confirmation outcomes. No probe refitting, threshold changes, additional temperatures, prefix choices or seed search occurred. Each retry method received exactly one identity-seeded potential attempt on every puzzle. Policy allocations were chosen without those retry outcomes. Already valid original boards were retained; retry boards were accepted only when two independent exact verifiers agreed.

The primary method forces the original level-6 code prefix, then samples later levels at temperature 0.5. Its official generation loop recomputes prefix attention; this is not cached prefix resumption. Deterministic forced-prefix replay matched the original and plain generator on all 32 prespecified checks. The sole fallback is a full stochastic restart at the same temperature, executed only after the primary failed its benefit gate.

Cohort: **project-held-out allocation/recovery cohort**. Original correctness: **590/1600 (36.88%)**. Fixed confidence retry budget: **272**. This cohort is now exposed and cannot become fresh confirmation again.

## Same retry-count comparison

Expected baselines are exact conditional averages over uniformly selected subsets of the same size; realized baselines use one frozen hash order. They never select using retry outcomes. The expected verifier-first comparator spends every retry on an independently verified original failure.

| Retry method | Confidence rescues | Random-all expected rescues | Verifier-first expected rescues | Random-all realized | Verifier-first realized | Gate |
|---|---:|---:|---:|---:|---:|---|
| level6_fixed_prefix_stochastic_suffix | 9 | 10.71 | 16.97 | 17 | 19 | Fail |
| full_stochastic_restart | 21 | 17.85 | 28.28 | 16 | 35 | Fail |

The required accuracy advantage is at least 0.5 percentage point over both expected count-matched baselines, with both two-sided 97.5% paired puzzle intervals above zero, plus a positive realized advantage under the common service envelope. The intervals account for the two predeclared retry methods; they condition on the fixed model/threshold and do not refit probes.

| Retry method | Advantage vs random-all (percentage points; interval) | Advantage vs verifier-first (percentage points; interval) | Selected-failure recovery | All-failure recovery |
|---|---|---|---:|---:|
| level6_fixed_prefix_stochastic_suffix | -0.107 [-0.456, +0.301] | -0.498 [-0.888, -0.080] | 3.72% | 6.24% |
| full_stochastic_restart | +0.197 [-0.321, +0.759] | -0.455 [-0.990, +0.108] | 8.68% | 10.40% |

## Measured monitoring and service cost

Twenty alternating paired trials on eight previously exposed calibration inputs at batch size 1 measured **137.80 ms** per plain solve and **147.39 ms** per monitored solve: **6.96%** mean overhead. The paired 95% overhead interval is **[5.96, 13.23] ms**. Timings synchronize CUDA and include full generation, final decoding and verification; the monitor additionally decodes the current prefix and scores it before future levels. These measurements are session/hardware specific, not production latency or a speedup claim.

For each retry method, the common conservative service envelope reserves the measured mean monitored baseline service plus the largest observed retry latency for each confidence retry. Baselines can use the monitor cost they avoid to buy additional retry slots. This is additive sequential replay accounting, not a live real-time controller or an equal-FLOP claim.

| Retry method | Confidence retry slots | Random-all / verifier-first slots | Confidence rescues | Random-all / verifier-first rescues |
|---|---:|---:|---:|---:|
| level6_fixed_prefix_stochastic_suffix | 272 | 317 / 317 | 9 | 18 / 26 |
| full_stochastic_restart | 272 | 330 / 330 | 21 | 21 / 41 |

## Evidence, resources and stopping

The separate cumulative ledger charged **510.32 GPU-assisted elapsed seconds**, **4936 puzzle generation calls**, **zero fits**, and **5,952,740 raw-record bytes**, within the frozen 1,200-second/8,000-call/200-MiB limits. Failed operations would also count. All work used the existing local checkpoint/GPU. The old V2 ledger and its failed gate remain unchanged.

The warning predicts errors at limited coverage; that alone does not establish recoverability. Exact final verification is a strong Sudoku baseline. The paired recovery table is a prespecified follow-on on the same project-held-out cohort, not a second independent confirmation sample. Training exposure is unknown. Conditional puzzle intervals omit model/threshold fitting uncertainty, and timing uncertainty is reported separately.

[Recovery record](../continuation/recovery.json), [timing measurements](../continuation/timing.json), [independent artifact audit](../continuation/audit.json), and [frozen protocol](../../configs/confidence_allocation.json) retain the details. The audit sidecar corrects the shared provenance helper's module-style command display to the actual script invocations while preserving original run manifests and executed source snapshots.

Reproduce the retained-data audit with `.venv\Scripts\python.exe scripts/audit_confidence_allocation.py`. The scientific commands intentionally refuse an unplanned repeat. Evidence archive restoration and verification instructions are in [the follow-on reproduction guide](../../docs/reproduce_confidence_allocation.md).

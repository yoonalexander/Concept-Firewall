"""Render the completed frozen allocation study without more experiments."""
from pathlib import Path

from concept_firewall.confidence_allocation import BASE, read_json


def main():
    root = Path(__file__).resolve().parents[1]
    confirmation = read_json(root/BASE/'confirmation.json')
    recovery = read_json(root/BASE/'recovery.json')
    timing = read_json(root/BASE/'timing.json')
    if recovery['status'] != 'completed':
        raise ValueError('Completed recovery evidence required')
    policies = recovery['policies']
    success = recovery['any_recovery_gate_passed']
    lines = ['# Confidence allocation: measured recovery', '',
             '**Decision:** '+('A preregistered recovery policy passed the scoped comparison.' if success else
                              'Neither the primary recovery method nor the predeclared alternative established the required confidence-allocation advantage. Close this bounded follow-on.'), '',
             'The fixed warning score passed the separate held-out failure-enrichment screen. This phase asks the harder question: does allocating retries with that warning actually improve verified answers at comparable resources? The original V2 detector study remains closed and failed.', '',
             '## Fixed execution', '',
             'The protocol was committed and pushed before confirmation outcomes. No probe refitting, threshold changes, additional temperatures, prefix choices or seed search occurred. Each retry method received exactly one identity-seeded potential attempt on every puzzle. Policy allocations were chosen without those retry outcomes. Already valid original boards were retained; retry boards were accepted only when two independent exact verifiers agreed.', '',
             'The primary method forces the original level-6 code prefix, then samples later levels at temperature 0.5. Its official generation loop recomputes prefix attention; this is not cached prefix resumption. Deterministic forced-prefix replay matched the original and plain generator on all 32 prespecified checks. The sole fallback is a full stochastic restart at the same temperature, executed only after the primary failed its benefit gate.', '',
             f"Cohort: **{recovery['cohort']}**. Original correctness: **{confirmation['metrics']['successes']}/{confirmation['metrics']['puzzles']} ({1-confirmation['metrics']['failure_prevalence']:.2%})**. Fixed confidence retry budget: **{confirmation['metrics']['alerts']}**. This cohort is now exposed and cannot become fresh confirmation again.", '',
             '## Same retry-count comparison', '',
             'Expected baselines are exact conditional averages over uniformly selected subsets of the same size; realized baselines use one frozen hash order. They never select using retry outcomes. The expected verifier-first comparator spends every retry on an independently verified original failure.', '',
             '| Retry method | Confidence rescues | Random-all expected rescues | Verifier-first expected rescues | Random-all realized | Verifier-first realized | Gate |',
             '|---|---:|---:|---:|---:|---:|---|']
    for entry in policies:
        s = entry['statistics']
        lines.append(f"| {entry['policy']} | {s['confidence_recovered']} | {s['random_all']['expected_recovered']:.2f} | {s['verifier_first']['expected_recovered']:.2f} | {s['random_all']['realized_recovered']} | {s['verifier_first']['realized_recovered']} | {'Pass' if s['gate_passed'] else 'Fail'} |")
    lines += ['', 'The required accuracy advantage is at least 0.5 percentage point over both expected count-matched baselines, with both two-sided 97.5% paired puzzle intervals above zero, plus a positive realized advantage under the common service envelope. The intervals account for the two predeclared retry methods; they condition on the fixed model/threshold and do not refit probes.', '',
              '| Retry method | Advantage vs random-all (percentage points; interval) | Advantage vs verifier-first (percentage points; interval) | Selected-failure recovery | All-failure recovery |',
              '|---|---|---|---:|---:|']
    for entry in policies:
        s = entry['statistics']
        formatted = []
        for baseline in ('random_all', 'verifier_first'):
            lo, hi = s['paired_97_5_percent_intervals'][baseline]
            formatted.append(f"{100*s['accuracy_advantage_vs_expected'][baseline]:+.3f} [{100*lo:+.3f}, {100*hi:+.3f}]")
        lines.append(f"| {entry['policy']} | {formatted[0]} | {formatted[1]} | {s['confidence_selected_failure_recovery']:.2%} | {s['all_failure_recovery']:.2%} |")
    lines += ['', '## Measured monitoring and service cost', '',
              f"Twenty alternating paired trials on eight previously exposed calibration inputs at batch size 1 measured **{timing['plain_mean_ms']:.2f} ms** per plain solve and **{timing['monitored_mean_ms']:.2f} ms** per monitored solve: **{timing['mean_overhead_fraction']:.2%}** mean overhead. The paired 95% overhead interval is **[{timing['paired_overhead_95_interval_ms'][0]:.2f}, {timing['paired_overhead_95_interval_ms'][1]:.2f}] ms**. Timings synchronize CUDA and include full generation, final decoding and verification; the monitor additionally decodes the current prefix and scores it before future levels. These measurements are session/hardware specific, not production latency or a speedup claim.", '',
              'For each retry method, the common conservative service envelope reserves the measured mean monitored baseline service plus the largest observed retry latency for each confidence retry. Baselines can use the monitor cost they avoid to buy additional retry slots. This is additive sequential replay accounting, not a live real-time controller or an equal-FLOP claim.', '',
              '| Retry method | Confidence retry slots | Random-all / verifier-first slots | Confidence rescues | Random-all / verifier-first rescues |',
              '|---|---:|---:|---:|---:|']
    for entry in policies:
        s = entry['statistics']; b = s['service_budget']
        lines.append(f"| {entry['policy']} | {b['confidence_retry_slots']} | {b['random_retry_slots']} / {b['verifier_retry_slots']} | {s['confidence_recovered']} | {b['random_all_recovered']} / {b['verifier_first_recovered']} |")
    usage = recovery['budget']['used']
    lines += ['', '## Evidence, resources and stopping', '',
              f"The separate cumulative ledger charged **{usage['gpu_seconds']:.2f} GPU-assisted elapsed seconds**, **{usage['model_puzzles']} puzzle generation calls**, **zero fits**, and **{usage['feature_bytes']:,} raw-record bytes**, within the frozen 1,200-second/8,000-call/200-MiB limits. Failed operations would also count. All work used the existing local checkpoint/GPU. The old V2 ledger and its failed gate remain unchanged.", '',
              'The warning predicts errors at limited coverage; that alone does not establish recoverability. Exact final verification is a strong Sudoku baseline. The paired recovery table is a prespecified follow-on on the same project-held-out cohort, not a second independent confirmation sample. Training exposure is unknown. Conditional puzzle intervals omit model/threshold fitting uncertainty, and timing uncertainty is reported separately.', '',
              '[Recovery record](../continuation/recovery.json), [timing measurements](../continuation/timing.json), [independent artifact audit](../continuation/audit.json), and [frozen protocol](../../configs/confidence_allocation.json) retain the details. The audit sidecar corrects the shared provenance helper\'s module-style command display to the actual script invocations while preserving original run manifests and executed source snapshots.', '',
              'Reproduce the retained-data audit with `.venv\\Scripts\\python.exe scripts/audit_confidence_allocation.py`. The scientific commands intentionally refuse an unplanned repeat. Evidence archive restoration and verification instructions are in [the follow-on reproduction guide](../../docs/reproduce_confidence_allocation.md).', '']
    (root/'results/reports/confidence_allocation_recovery.md').write_text('\n'.join(lines), encoding='utf-8')
    print(root/'results/reports/confidence_allocation_recovery.md')


if __name__ == '__main__':
    main()

"""Read only recorded calibration features and a frozen probe; never run NCM."""
import json
from pathlib import Path

import numpy as np

from concept_firewall.artifacts import sha256_file
from concept_firewall.decision_value import allocation_summary, portable_scores, recovery_scenario
from concept_firewall.v2_protocol import write_json


def main():
    root = Path(__file__).resolve().parents[1]
    parent = root/'results/manifests/20261025T030127575557Z-v2-study.json'
    m = json.loads(parent.read_text())
    cap, probe = m['captures']['calibration'], m['models']['decoded_confidence']
    for entry in (cap, probe):
        if sha256_file(root/entry['file']) != entry['sha256']:
            raise ValueError('Recorded development artifact changed')
    record = json.loads((root/probe['file']).read_text())
    with np.load(root/cap['file'], allow_pickle=False) as data:
        scores = portable_scores(record, data['decoded_confidence'])
        summary = allocation_summary(data['y'], scores > record['threshold'])
    if summary['true_positives'] != 111 or summary['false_positives'] != 15:
        raise ValueError('Recorded development operating point did not reproduce')
    scenarios = [recovery_scenario(summary, q, damage, cost)
                 for q in (0, .1, .25, .5, 1) for damage in (0, .25) for cost in (.25, .5, 1)]
    output = root/'results/continuation/value_check.json'
    result = {'parent_manifest': parent.relative_to(root).as_posix(),
              'parent_sha256': sha256_file(parent), 'capture': cap, 'probe': probe,
              'scope': 'Exploratory saved calibration data; no new fits, model calls or confirmation access',
              'summary': summary, 'hypothetical_scenarios': scenarios,
              'decision': 'Small separate confirmation/allocation experiment justified; no recovery benefit established',
              'baseline_requirement': 'Include verifier-first random failed-puzzle retries; exact final verification can identify every failure',
              'reason': 'Potential allocation advantage exists over random-all, but selected failures must be more recoverable to beat verifier-first',
              'new_model_runs': 0, 'new_fits': 0, 'confirmation_accessed': False,
              'old_study_reopened': False}
    write_json(output, result)
    lines = ['# Saved-results value check', '',
             'The original V2 study remains closed at its failed detector gate. This analysis uses only its saved 800 calibration rows and the unchanged board+confidence probe. It reproduces 111 detected failures and 15 false alarms; no fitting, GPU generation or confirmation access occurred.', '',
             '## What the signal could buy', '',
             f"Alerts cover {summary['alert_fraction']:.2%} of puzzles and contain {summary['alert_precision']:.2%} failures, compared with {summary['failure_prevalence']:.2%} overall. A hypothetical perfect retry could add at most {summary['perfect_retry_gain_ceiling']:.2%} accuracy. Against randomly allocating the same number of retries across all puzzles, its hypothetical advantage ceiling is {summary['perfect_retry_advantage_over_random_all']:.2%} of puzzles.", '',
             'Those are bounds, not observed improvements. An identical deterministic retry changes nothing. A retry needs a different sampling policy, and preserving an already valid first answer prevents damage. With zero monitoring cost and retry cost equal to one baseline solve, recovery of approximately 44% of alerted failures would be needed merely to improve correct answers per unit compute. Actual monitoring costs raise this requirement.', '',
             '## The stronger baseline', '',
             f"Sudoku has an exact final verifier. A verifier-first policy can spend every retry on a failure. Confidence selection has {summary['alert_precision']:.2%} failure precision, so its selected failures would need roughly {summary['selected_recovery_ratio_needed_vs_verifier_first']:.3f} times the recovery probability of verifier-selected failures to offset those wasted retries, before monitoring overhead. The same recovery probability everywhere favors verifier-first. Early failure discrimination alone cannot establish value.", '',
             '## Decision', '',
             'Proceed with one separately registered study of the already saved board+confidence score. First confirm that its fixed alerts enrich failures over random allocation at a bounded alert rate. If that passes, evaluate one fixed stochastic continuation policy and compare actual solved outcomes with random-all and verifier-first at matched retry counts. Count recomputed prefixes and monitoring work; do not call this an efficient prefix-resume implementation. No new probe fits, layers, thresholds or temperature search.', '',
             'The confirmation question is narrower than the old 40% recall claim. No new result can turn the old failed gate into a pass. Unsuccessful recovery should close this follow-on with the stronger baseline identified, rather than trigger more detector fishing.', '',
             'Detailed scenario assumptions, costs and source hashes: [value_check.json](../continuation/value_check.json). Reproduce: `.venv\\Scripts\\python.exe scripts/check_confidence_value.py`.']
    (root/'results/reports/confidence_value_check.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()

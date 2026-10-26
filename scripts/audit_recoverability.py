"""Independently replay saved OOF allocations and resource accounting; zero fits."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time
import sys

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from concept_firewall.diagnostics import independent_inspection


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(value):
    return hashlib.sha256(('recoverability-exploration-v1:'+value).encode()).hexdigest()


def selection(rows, name, budget):
    by_fold = [[r for r in rows if r['fold'] == f] for f in range(5)]
    ideal = [len(v)*budget/len(rows) for v in by_fold]
    quota = [math.floor(v) for v in ideal]
    for f in sorted(range(5), key=lambda f: (-(ideal[f]-quota[f]), f))[:budget-sum(quota)]:
        quota[f] += 1
    return {r['puzzle_id'] for f in range(5) for r in sorted(by_fold[f], key=lambda r: (-r['scores'][name], key(r['puzzle_id'])))[:quota[f]]}


def main(source, root):
    start, wall = time.process_time(), time.monotonic()
    out = root/'results/recoverability'
    p = read(root/'configs/recoverability_analysis.json')
    inventory = read(out/'inventory.json')
    result = read(out/'results.json')
    ledger = read(out/'ledger.json')
    replay = read(out/'replay_manifest.json')
    for name, item in inventory['files'].items():
        assert sha(source/name) == item['sha256'], name
    assert sha(root/'configs/recoverability_analysis.json') == replay['protocol_sha256'] == ledger['protocol_sha256']
    assert sha(out/'results.json') == replay['results_sha256']
    assert sha(out/'oof_predictions.jsonl') == replay['predictions_sha256']
    assert sha(root/'src/concept_firewall/recoverability_analysis.py') == replay['implementation_sha256']
    assert ledger['status'] == 'completed' and ledger['fit_jobs'] == 40
    assert len(ledger['events']) == 40 and all(e['status'] == 'completed' for e in ledger['events'])
    assert len({(e['action'], e['model'], e['fold']) for e in ledger['events']}) == 40
    base = [json.loads(s) for s in (source/'results/continuation/raw/confirmation.jsonl').read_text().splitlines()]
    predictions = [json.loads(s) for s in (out/'oof_predictions.jsonl').read_text().splitlines()]
    failure = {r['puzzle_id']: not independent_inspection(r['puzzle'], r['final_board'])['valid'] for r in base}
    assert sum(failure.values()) == 1010
    mapping = {g: i % 5 for i, g in enumerate(sorted({r['group'] for r in base}, key=key))}
    base_map = {r['puzzle_id']: r for r in base}
    # Independent construction of input/prefix additions to the saved 14-vector.
    x = {}
    for r in base:
        cells = np.array([int(c) != 0 for c in r['puzzle']]).reshape(9, 9)
        counts = Counter(r['prefix'])
        prefix_entropy = -sum((c/35)*math.log2(c/35) for c in counts.values())
        x[r['puzzle_id']] = np.array(r['features']+[float(cells.sum()), float(cells.sum(1).min()), float(cells.sum(1).max()),
                                   float(cells.sum(0).min()), float(cells.sum(0).max()), prefix_entropy, len(counts)/35])
    checks = []
    for action in p['actions']:
        rows = [r for r in predictions if r['action'] == action]
        assert len(rows) == 1010 and len({r['puzzle_id'] for r in rows}) == 1010
        retry = {r['puzzle_id']: r for r in (json.loads(s) for s in (source/f'results/continuation/raw/{action}.jsonl').read_text().splitlines())}
        for r in rows:
            before = base_map[r['puzzle_id']]
            assert failure[r['puzzle_id']] and r['group'] == before['group'] and r['fold'] == mapping[r['group']]
            assert r['rescued'] == independent_inspection(before['puzzle'], retry[r['puzzle_id']]['retry_board'])['valid']
        rescues = sum(r['rescued'] for r in rows)
        a = result['actions'][action]
        assert rescues == a['potential_rescues']
        assert a['original_confidence_alert_rescues'] == sum(r['rescued']*base_map[r['puzzle_id']]['alert'] for r in rows)
        for family, audits in a['fit_audit'].items():
            for audit in audits:
                train = [x[r['puzzle_id']] for r in rows if r['fold'] != audit['fold']]
                assert len(train) == audit['train_rows']
                if audit['training_mean']:
                    cols = slice(14, 19) if family == 'input_logistic' else slice(0, 14) if family == 'decoded_logistic' else slice(None)
                    np.testing.assert_allclose(np.array(train)[:, cols].mean(0), audit['training_mean'], rtol=0, atol=1e-12)
        for name, metrics in a['models'].items():
            for b in metrics['budgets']:
                selected = selection(rows, name, b['budget'])
                actual = sum(r['rescued'] for r in rows if r['puzzle_id'] in selected)
                assert len(selected) == b['budget'] and actual == b['rescues']
                assert abs(b['uniform_expected']-b['budget']*rescues/1010) < 1e-10
                s = b['service']
                slot = max(r['elapsed_ms'] for r in retry.values())
                expected_slots = min(1010, math.floor(b['budget']+1600*result['timing']['overhead_ms']/slot+1e-10))
                assert s['random_slots'] == expected_slots
                own = b['budget'] if s['monitor_charged'] else expected_slots
                service_ids = selection(rows, name, own)
                assert s['policy_rescues'] == sum(r['rescued'] for r in rows if r['puzzle_id'] in service_ids)
                assert abs(s['uniform_expected']-expected_slots*rescues/1010) < 1e-10
        checks.append({'action': action, 'potential_rescues': rescues, 'original_alert_rescues': a['original_confidence_alert_rescues'], 'ranked_policy_budget_checks': 30})
    cpu = time.process_time()-start
    audit = {'status': 'passed', 'new_fits': 0, 'new_model_outputs': 0, 'actions': checks,
             'protected_source_hashes_unchanged': True, 'train_only_scaler_means_verified': True,
             'fold_identity_verified': True, 'cpu_seconds': cpu, 'wall_seconds': time.monotonic()-wall,
             'analysis_plus_audit_cpu_seconds': ledger['cpu_seconds']+cpu,
             'uncertainty': 'Intervals retain their conditional fixed-OOF-score scope; this audit replays point estimates, not additional statistical fits'}
    assert audit['analysis_plus_audit_cpu_seconds'] < p['limits']['cpu_seconds']
    (out/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    main(args.source_root.resolve(), Path(__file__).resolve().parents[1])

"""Independently verify retained follow-on outcomes/counts; no model or fit calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from concept_firewall.artifacts import sha256_file
from concept_firewall.confidence_allocation import BASE, PROTOCOL, confirmation_statistics, read_json, require_frozen
from concept_firewall.decision_value import portable_scores
from concept_firewall.diagnostics import independent_inspection
from concept_firewall.probes import feature_vector
from concept_firewall.representations import extract_features
from concept_firewall.schema import LevelState, puzzle_identity
from concept_firewall.v2_data import DATA_MANIFEST
from concept_firewall.v2_protocol import write_json


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def raw_rows(root, entry):
    path = root/entry['raw_file']
    check(sha256_file(path) == entry['raw_sha256'], 'Raw file digest mismatch')
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    p, frozen = require_frozen(root)
    confirmation = read_json(root/BASE/'confirmation.json')
    recovery = read_json(root/BASE/'recovery.json')
    check(confirmation['status'] == recovery['status'] == 'completed', 'Completed evidence required')
    rows = raw_rows(root, confirmation)
    partition = read_json(root/DATA_MANIFEST)['partitions']['confirmation']
    check([r['puzzle_id'] for r in rows] == partition['puzzle_ids'], 'Frozen puzzle identity order changed')
    check([r['group'] for r in rows] == partition['groups'], 'Frozen groups changed')
    check(len(set(r['puzzle_id'] for r in rows)) == len(rows), 'Repeated identities')
    model = read_json(root/BASE/'probe.json')
    failures = 0
    alerted_failures = 0
    alerted_successes = 0
    for row in rows:
        check(hashlib.sha256(row['puzzle'].encode()).hexdigest() == row['puzzle_id'], 'Puzzle input identity mismatch')
        valid = independent_inspection(row['puzzle'], row['final_board'])['valid']
        check(int(not valid) == row['y'], 'Independent baseline outcome differs')
        check(len(row['codes']) == 322 and row['prefix'] == row['codes'][:35], 'Malformed baseline codes/prefix')
        codes, offset = [], 0
        for length in (1, 2, 4, 6, 9, 13):
            codes.append(tuple(row['prefix'][offset:offset+length]))
            offset += length
        state = LevelState('audit', puzzle_identity(row['puzzle']), 'audit', 6, tuple(codes), row['current_board'])
        decoded = feature_vector(extract_features(state, row['puzzle']), state.codes_prefix, 'decoded')[1]
        check(list(decoded) == row['features'][:-6], 'Current-board feature replay differs')
        score = float(portable_scores(model, [row['features']])[0])
        check(abs(score-row['score']) < 1e-10 and (score > model['threshold']) == row['alert'], 'Frozen probe decision differs')
        failures += int(not valid)
        alerted_failures += int(row['alert'] and not valid)
        alerted_successes += int(row['alert'] and valid)
    stats = confirmation['metrics']
    check((failures, alerted_failures, alerted_successes) ==
          (stats['failures'], stats['true_positives'], stats['false_positives']), 'Independent confirmation counts differ')
    repeat = confirmation_statistics(np.array([r['y'] for r in rows]), np.array([r['alert'] for r in rows]), p)
    check(repeat['conditions'] == confirmation['conditions'] and repeat['metrics'] == stats, 'Screen calculation differs')
    audits = []
    for entry in recovery['policies']:
        retries = raw_rows(root, entry)
        check([r['puzzle_id'] for r in retries] == [r['puzzle_id'] for r in rows], 'Retry identity order changed')
        fixed_suffix = entry['policy'] == p['recovery']['primary']
        successes, selected_successes = [], []
        for before, retry in zip(rows, retries):
            expected_seed = int(hashlib.sha256(f"{p['study_id']}:{entry['policy']}:{retry['puzzle_id']}:{p['recovery']['seed']}".encode()).hexdigest()[:8], 16)
            check(retry['seed'] == expected_seed, 'Identity seed changed')
            check(len(retry['retry_codes']) == 322, 'Incomplete retry codes')
            if fixed_suffix:
                check(retry['retry_codes'][:35] == before['prefix'], 'Stochastic suffix changed fixed prefix')
            valid = independent_inspection(before['puzzle'], retry['retry_board'])['valid']
            check(valid == retry['retry_valid'], 'Independent retry outcome differs')
            rescued = int(before['y'] == 1 and valid)
            successes.append(rescued)
            selected_successes.append(rescued*before['alert'])
        metrics = entry['statistics']
        total, targeted, m = sum(successes), sum(selected_successes), stats['alerts']
        check(total == metrics['all_failures_recovered_by_potential_retry'] and targeted == metrics['confidence_recovered'], 'Independent recovery counts differ')
        check(abs(metrics['random_all']['expected_recovered']-m*total/len(rows)) < 1e-10, 'Random-all expectation differs')
        check(abs(metrics['verifier_first']['expected_recovered']-m*total/failures) < 1e-10, 'Verifier-first expectation differs')
        # Independently reproduce realized allocations and their resource slots.
        for name, label in (('random_all', 'random-all'), ('verifier_first', 'verifier-first')):
            ordered = sorted(range(len(rows)), key=lambda i: hashlib.sha256(f"confidence-allocation-v1:{label}:{rows[i]['puzzle_id']}:{p['recovery']['seed']}".encode()).hexdigest())
            if name == 'verifier_first':
                ordered = [i for i in ordered if rows[i]['y']]
            actual = sum(successes[i] for i in ordered[:m])
            check(actual == metrics[name]['realized_recovered'], 'Hash-selected baseline differs')
            slot_key = 'random_retry_slots' if name == 'random_all' else 'verifier_retry_slots'
            count_key = 'random_all_recovered' if name == 'random_all' else 'verifier_first_recovered'
            budget = metrics['service_budget']
            check(sum(successes[i] for i in ordered[:budget[slot_key]]) == budget[count_key], 'Service-budget baseline differs')
        check(all(metrics['service_budget'][name] <= metrics['service_budget']['milliseconds']+1e-7 for name in
                  ('confidence_slot_envelope_ms', 'random_slot_envelope_ms', 'verifier_slot_envelope_ms')), 'Policy service envelope exceeded')
        audits.append({'policy': entry['policy'], 'outcomes_checked': len(retries), 'rescues': total, 'selected_rescues': targeted,
                       'fixed_prefixes_checked': len(retries) if fixed_suffix else 0,
                       'baseline_expectations_and_realizations_match': True})
    ledger = read_json(root/BASE/'runtime/ledger.json')
    check(ledger['active'] is None and ledger['used']['fit_jobs'] == 0, 'Ledger active or fits charged')
    check(all(ledger['used'][k] <= v for k, v in p['limits'].items()), 'Study allowance exceeded')
    check(ledger['used']['model_puzzles'] == recovery['budget']['used']['model_puzzles'], 'Final model-call accounting differs')
    # Retain the helper's historically inaccurate module-style command without
    # rewriting immutable run manifests; attach exact script invocation here.
    commands = []
    for entry, step in ((confirmation, 'confirm'), (recovery, 'recover')):
        manifest_path = root/'results/manifests'/f"{entry['run_manifest']}.json"
        manifest = read_json(manifest_path)
        check(sha256_file(root/manifest['source_snapshot']) == manifest['source_snapshot_sha256'], 'Executed source ZIP changed')
        commands.append({'run_manifest': manifest_path.relative_to(root).as_posix(),
                         'manifest_sha256': sha256_file(manifest_path), 'recorded_helper_command': manifest['command'],
                         'actual_script_command': [manifest['command'][0], 'scripts/confidence_allocation.py', step],
                         'note': 'Shared manifest helper assumed module CLI; actual execution used the script. Original manifest preserved.'})
    result = {'status': 'passed', 'baseline_outcomes_checked': len(rows), 'policies': audits,
              'frozen_probe_decisions_checked': len(rows), 'original_V2_artifacts_and_ledger_unchanged': True,
              'protocol_sha256': frozen['protocol_sha256'], 'command_records': commands,
              'audit_script_sha256': sha256_file(Path(__file__)),
              'audit_command': [sys.executable, 'scripts/audit_confidence_allocation.py', '--root', str(root)],
              'budget': ledger['used'], 'new_model_calls': 0, 'new_fits': 0}
    write_json(root/BASE/'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

"""Measured retries and allocation replay for one frozen follow-on protocol."""
from __future__ import annotations

import hashlib
import json
import math
import sys

from .artifacts import sha256_file, verified_artifacts
from .confidence_allocation import BASE, PARENT, ConfidenceMonitor, read_json, require_frozen
from .provenance import new_manifest, require_upstream, save_manifest
from .v2_protocol import BudgetLedger, write_json


def identity_seed(study_id, policy, puzzle_id, seed):
    return int(hashlib.sha256(f'{study_id}:{policy}:{puzzle_id}:{seed}'.encode()).hexdigest()[:8], 16)


def retry_codes(adapter, context, *, prefix, level, temperature, seed):
    """Recompute the official loop, forcing a prefix before stochastic sampling.

    This deliberately does not claim cached prefix resumption. The full loop's
    prefix attention is recomputed and charged even when codes are forced.
    """
    import torch
    model = adapter.generator
    if '_sample_level' in model.__dict__ or adapter.generation_settings.cfg_scale:
        raise ValueError('Sampling override/CFG is unsupported')
    if not model.query_level0 or model.l0_ar or not 1 <= level <= len(adapter.levels):
        raise ValueError('Unsupported forced-prefix path')
    if not math.isfinite(temperature) or temperature < 0:
        raise ValueError('Invalid retry temperature')
    if prefix is not None and prefix.shape != (len(context), sum(adapter.levels[:level])):
        raise ValueError('Prefix has wrong batch/length')
    original = model._sample_level
    index, offset = 0, 0

    def sample(logits, *_args, **_kwargs):
        nonlocal index, offset
        if index >= len(adapter.levels) or logits.shape[:2] != (len(context), adapter.levels[index]):
            raise ValueError('Unexpected generation level/shape')
        if prefix is not None and index < level:
            length = adapter.levels[index]
            selected = prefix[:, offset:offset+length].clone()
            if selected.dtype != torch.long or bool((selected < 0).any()) or bool((selected >= logits.shape[-1]).any()):
                raise ValueError('Prefix contains invalid codes')
            offset += length
        else:
            selected = original(logits, temperature, 0, 1.0)
        index += 1
        return selected

    devices = list(range(torch.cuda.device_count())) if str(adapter.device).startswith('cuda') else []
    model._sample_level = sample
    try:
        with torch.random.fork_rng(devices=devices), torch.no_grad():
            torch.manual_seed(seed)
            codes = adapter.generate(context)
        if index != len(adapter.levels):
            raise ValueError('Incomplete retry generation')
        if prefix is not None and not torch.equal(codes[:, :prefix.shape[1]], prefix):
            raise ValueError('Retry did not retain the fixed prefix')
        return codes
    finally:
        del model._sample_level


def hash_order(ids, label, seed):
    return sorted(range(len(ids)), key=lambda i: hashlib.sha256(f'confidence-allocation-v1:{label}:{ids[i]}:{seed}'.encode()).hexdigest())


def recovery_statistics(y, alerts, retry_valid, ids, retry_ms, timing, protocol):
    import numpy as np
    y, alerts, retry_valid = np.asarray(y), np.asarray(alerts), np.asarray(retry_valid)
    times = np.asarray(retry_ms, dtype=float)
    n = len(y)
    if any(v.shape != (n,) for v in (alerts, retry_valid, times)) or n != len(ids) or n == 0:
        raise ValueError('Misaligned recovery table')
    if not np.isin(y, [0, 1]).all() or alerts.dtype != bool or retry_valid.dtype != bool:
        raise ValueError('Invalid recovery outcomes/alerts')
    if not np.isfinite(times).all() or (times <= 0).any() or len(set(ids)) != n:
        raise ValueError('Invalid timing or duplicate puzzle identity')
    fail = y == 1
    rescue = fail & retry_valid
    m, failures, base = int(alerts.sum()), int(fail.sum()), int((~fail).sum())
    if not 0 < m <= failures or failures == n:
        raise ValueError('Both classes and enough failures for matched allocation required')
    selected_rescues = int(rescue[alerts].sum())
    total_rescues = int(rescue.sum())
    seed = protocol['recovery']['seed']
    random_order = hash_order(ids, 'random-all', seed)
    verifier_order = [i for i in hash_order(ids, 'verifier-first', seed) if fail[i]]
    random_rescues = int(rescue[random_order[:m]].sum())
    verifier_rescues = int(rescue[verifier_order[:m]].sum())
    expected_random = m*total_rescues/n
    expected_verifier = m*total_rescues/failures
    # Multinomial puzzle bootstrap is equivalent to sampling aligned rows with
    # replacement; recompute alert/failure counts for every paired draw.
    categories = y.astype(int)*4+alerts.astype(int)*2+rescue.astype(int)
    counts = np.bincount(categories, minlength=8)
    draws = np.random.default_rng(protocol['bootstrap_seed']).multinomial(n, counts/n, protocol['bootstrap_draws'])
    ms = draws[:, [2, 3, 6, 7]].sum(1)
    fs = draws[:, 4:].sum(1)
    rs = draws[:, [1, 3, 5, 7]].sum(1)
    ts = draws[:, [3, 7]].sum(1)
    random_delta = (ts-ms*rs/n)/n
    verifier_delta = (ts-ms*rs/np.maximum(fs, 1))/n
    intervals = {name: [float(v) for v in np.quantile(values, [.0125, .9875])]
                 for name, values in (('random_all', random_delta), ('verifier_first', verifier_delta))}
    plain_ms, monitored_ms = timing['plain_mean_ms'], timing['monitored_mean_ms']
    if not all(math.isfinite(v) and v > 0 for v in (plain_ms, monitored_ms)):
        raise ValueError('Positive service time measurements required')
    retry_slot = float(times.max())
    common_budget = n*monitored_ms+m*retry_slot
    baseline_slots = max(0, math.floor((common_budget-n*plain_ms)/retry_slot+1e-10))
    random_slots, verifier_slots = min(n, baseline_slots), min(failures, baseline_slots)
    cost_random = int(rescue[random_order[:random_slots]].sum())
    cost_verifier = int(rescue[verifier_order[:verifier_slots]].sum())
    point = {'random_all': (selected_rescues-expected_random)/n,
             'verifier_first': (selected_rescues-expected_verifier)/n}
    minimum = protocol['recovery']['minimum_accuracy_advantage']
    conditions = {'minimum_gain_vs_both_expected_matched_count_baselines': all(v >= minimum for v in point.values()),
                  'both_bonferroni_interval_lower_bounds_positive': all(v[0] > 0 for v in intervals.values()),
                  'wins_against_both_realized_service_budget_baselines': selected_rescues > max(cost_random, cost_verifier)}
    return {'puzzles': n, 'original_solved': base, 'original_failures': failures, 'retry_budget': m,
            'all_failures_recovered_by_potential_retry': total_rescues,
            'confidence_recovered': selected_rescues,
            'confidence_solved': base+selected_rescues,
            'confidence_accuracy': (base+selected_rescues)/n,
            'confidence_selected_failure_recovery': selected_rescues/int((fail & alerts).sum()) if (fail & alerts).any() else 0,
            'all_failure_recovery': total_rescues/failures,
            'random_all': {'realized_recovered': random_rescues, 'expected_recovered': expected_random, 'solved': base+random_rescues},
            'verifier_first': {'realized_recovered': verifier_rescues, 'expected_recovered': expected_verifier, 'solved': base+verifier_rescues},
            'accuracy_advantage_vs_expected': point, 'paired_97_5_percent_intervals': intervals,
            'service_budget': {'milliseconds': common_budget, 'worst_observed_retry_ms': retry_slot,
                               'plain_mean_ms': plain_ms, 'monitored_mean_ms': monitored_ms,
                               'confidence_retry_slots': m, 'random_retry_slots': random_slots, 'verifier_retry_slots': verifier_slots,
                               'random_all_recovered': cost_random, 'verifier_first_recovered': cost_verifier,
                               'confidence_slot_envelope_ms': n*monitored_ms+m*retry_slot,
                               'random_slot_envelope_ms': n*plain_ms+random_slots*retry_slot,
                               'verifier_slot_envelope_ms': n*plain_ms+verifier_slots*retry_slot,
                               'limits': 'Replay of measured sequential service demand; maximum is observed, not a guaranteed latency bound'},
            'conditions': conditions, 'gate_passed': all(conditions.values()),
            'unchanged_successes_preserved': True,
            'uncertainty_scope': 'Puzzle bootstrap for the fixed probe, threshold and one identity-seeded retry procedure; no refits; timing uncertainty separate'}


def profile_monitor(root, adapter, monitor, ledger, protocol):
    import numpy as np
    import torch
    from .sudoku_labels import validate_sudoku
    from .timing import timed_call
    from .v2_data import load_partition
    from .v2_training import encode_puzzle
    target = root/BASE/'timing.json'
    if target.exists():
        raise ValueError('Timing experiment already attempted')
    write_json(target, {'status': 'running'})
    rows = load_partition(root, 'calibration')[:protocol['timing']['warmup_puzzles']]
    contexts = [adapter.prepare_context([encode_puzzle(r['puzzle'])]) for r in rows]

    def solve(index, monitored):
        row = rows[index]
        codes = monitor.generate(contexts[index], [row['puzzle']])[0] if monitored else adapter.generate(contexts[index])
        board = adapter.decode_final(codes)[0]
        return codes, board, validate_sudoku(row['puzzle'], board).is_valid

    with ledger.operation('timing warmup', timed_resource='gpu_seconds', model_puzzles=2*len(rows)):
        for i in range(len(rows)):
            a, b = solve(i, False), solve(i, True)
            if not torch.equal(a[0], b[0]) or a[1:] != b[1:]:
                raise ValueError('Timing monitor changed generated outcome')
        torch.cuda.synchronize()
    pairs = []
    for pair in range(protocol['timing']['pairs']):
        with ledger.operation(f'timing pair {pair}', timed_resource='gpu_seconds', model_puzzles=2):
            measurements = {}
            for observed in ((False, True) if pair % 2 == 0 else (True, False)):
                result = timed_call(lambda: solve(pair % len(rows), observed), device=adapter.device)
                measurements['monitored_ms' if observed else 'plain_ms'] = result.elapsed_ms
            pairs.append(measurements)
    plain = np.array([v['plain_ms'] for v in pairs])
    monitored = np.array([v['monitored_ms'] for v in pairs])
    rng = np.random.default_rng(protocol['bootstrap_seed'])
    bootstrap = (monitored-plain)[rng.integers(len(pairs), size=(10000, len(pairs)))].mean(1)
    result = {'status': 'completed', 'batch_size': 1, 'pairs': pairs,
              'plain_mean_ms': float(plain.mean()), 'monitored_mean_ms': float(monitored.mean()),
              'mean_overhead_ms': float((monitored-plain).mean()),
              'mean_overhead_fraction': float(monitored.mean()/plain.mean()-1),
              'paired_overhead_95_interval_ms': np.quantile(bootstrap, [.025, .975]).tolist(),
              'scope': 'Synchronized full generation, final decoding and exact verification; monitor also reconstructs/decodes current prefix and scores before future levels',
              'population': 'Eight already exposed calibration inputs, 20 alternated paired trials; hardware/session specific, not a production benchmark'}
    write_json(target, result)
    return result


def recovery_rows(root, confirmation):
    if confirmation.get('status') == 'completed' and confirmation.get('gate_passed'):
        path = root/confirmation['raw_file']
        if sha256_file(path) != confirmation['raw_sha256']:
            raise ValueError('Confirmation raw records changed')
        return [json.loads(line) for line in path.read_text().splitlines()], 'project-held-out allocation/recovery cohort'
    # The predeclared alternative after an unsuccessful screen uses only exposed
    # calibration data, never a replacement "fresh" split.
    import numpy as np
    from .decision_value import portable_scores
    from .v2_data import load_partition
    parent = read_json(root/PARENT)
    capture = parent['captures']['calibration']
    audit = read_json(root/'results/manifests/20261025T030920192150Z-v2-outcome-audit.json')
    if sha256_file(root/capture['file']) != capture['sha256'] or sha256_file(root/audit['raw_file']) != audit['raw_sha256']:
        raise ValueError('Development fallback evidence changed')
    with np.load(root/capture['file'], allow_pickle=False) as data:
        model = read_json(root/BASE/'probe.json')
        scores = portable_scores(model, data['decoded_confidence'])
    originals = {r['puzzle_id']: r for r in (json.loads(line) for line in (root/audit['raw_file']).read_text().splitlines()) if r['role'] == 'calibration'}
    rows = []
    for row, score in zip(load_partition(root, 'calibration'), scores):
        raw = originals[row['puzzle_id']]
        rows.append({**row, **raw, 'score': float(score), 'alert': bool(score > model['threshold']),
                     'prefix': raw['codes'][:35], 'y': int(not raw['final_valid'])})
    return rows, 'exploratory exposed-calibration fallback; no confirmation claim'


def run_recovery(root):
    import torch
    from .upstream_adapter import NCMAdapter
    from .v2_training import encode_puzzle
    p, frozen = require_frozen(root)
    target = root/BASE/'recovery.json'
    if target.exists():
        raise ValueError('Recovery already attempted; refusing a policy/seed search')
    confirmation = read_json(root/BASE/'confirmation.json')
    rows, scope = recovery_rows(root, confirmation)
    require_upstream(root)
    if verified_artifacts(root) != frozen['artifact_sha256']:
        raise ValueError('Official artifacts changed')
    ledger = BudgetLedger(root/BASE/'runtime/ledger.json', frozen['protocol_sha256'], p['limits'])
    manifest = new_manifest(root, 'allocation-recovery', {'protocol_sha256': frozen['protocol_sha256'], 'cohort': scope, 'fits': 0})
    manifest['command'] = [sys.executable, str(root/'scripts/confidence_allocation.py'), 'recover']
    save_manifest(root, manifest)
    write_json(target, {'status': 'running', 'run_manifest': manifest['run_id']})
    try:
        with ledger.operation('load recovery model', timed_resource='gpu_seconds'):
            adapter = NCMAdapter.load(root/'third_party/ncm', root/'third_party/ncm/config/eval/sudoku-hard.yaml', root/'artifacts/sudoku-hard', device='cuda')
            monitor = ConfidenceMonitor(adapter, read_json(root/BASE/'probe.json'), p['level'])
            torch.cuda.synchronize()
        timing = profile_monitor(root, adapter, monitor, ledger, p)
        checks = p['recovery']['deterministic_prefix_checks']
        for start in range(0, checks, p['batch_size']):
            batch = rows[start:start+p['batch_size']]
            with ledger.operation(f'forced-prefix deterministic check {start}', timed_resource='gpu_seconds', model_puzzles=2*len(batch)):
                context = adapter.prepare_context([encode_puzzle(row['puzzle']) for row in batch])
                prefix = torch.tensor([r['prefix'] for r in batch], device=adapter.device)
                plain = adapter.generate(context)
                forced = retry_codes(adapter, context, prefix=prefix, level=p['level'], temperature=0, seed=p['recovery']['seed'])
                if not torch.equal(plain, forced) or plain.cpu().tolist() != [r['codes'] for r in batch]:
                    raise ValueError('Deterministic prefix replay differs from plain/frozen generator')
                torch.cuda.synchronize()
        write_json(root/BASE/'prefix_equivalence.json', {'status': 'passed', 'puzzles': checks,
                   'all_codes_equal_to_unobserved_and_frozen': True, 'prefix_attention_recomputed': True})
        policies = []
        for policy in (p['recovery']['primary'], p['recovery']['alternative']):
            result = run_policy(root, adapter, rows, timing, ledger, p, policy)
            policies.append(result)
            if result['statistics']['gate_passed']:
                break
        result = {'status': 'completed', 'cohort': scope, 'policies': policies,
                  'any_recovery_gate_passed': any(r['statistics']['gate_passed'] for r in policies),
                  'timing_file': (BASE/'timing.json').as_posix(), 'timing_sha256': sha256_file(root/BASE/'timing.json'),
                  'run_manifest': manifest['run_id'], 'budget': ledger.snapshot(), 'new_fits': 0,
                  'old_study_reopened': False, 'protocol_sha256': frozen['protocol_sha256']}
        write_json(target, result)
        manifest.update(status='passed', recovery_gate_passed=result['any_recovery_gate_passed'],
                        result_file=target.relative_to(root).as_posix(), result_sha256=sha256_file(target), budget=ledger.snapshot())
    except BaseException as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}', budget=ledger.snapshot())
        write_json(target, {'status': 'failed', 'error': manifest['error'], 'run_manifest': manifest['run_id']})
        save_manifest(root, manifest)
        raise
    save_manifest(root, manifest)
    return target


def run_policy(root, adapter, rows, timing, ledger, p, policy):
    import numpy as np
    import torch
    from .diagnostics import independent_inspection
    from .sudoku_labels import validate_sudoku
    from .timing import timed_call
    from .v2_training import encode_puzzle
    raw = root/BASE/'raw'/f'{policy}.jsonl'
    if raw.exists():
        raise ValueError('Potential retry table already exists')
    records = []
    for start in range(0, len(rows), p['batch_size']):
        batch = rows[start:start+p['batch_size']]
        with ledger.operation(f'{policy} {start}', timed_resource='gpu_seconds', model_puzzles=len(batch)):
            for row in batch:
                seed = identity_seed(p['study_id'], policy, row['puzzle_id'], p['recovery']['seed'])
                context = adapter.prepare_context([encode_puzzle(row['puzzle'])])
                prefix = torch.tensor([row['prefix']], device=adapter.device) if policy == p['recovery']['primary'] else None

                def generate():
                    codes = retry_codes(adapter, context, prefix=prefix, level=p['level'], temperature=p['recovery']['temperature'], seed=seed)
                    board = adapter.decode_final(codes)[0]
                    valid = validate_sudoku(row['puzzle'], board).is_valid
                    return codes, board, valid

                measured = timed_call(generate, device=adapter.device)
                codes, board, valid = measured.value
                if valid != independent_inspection(row['puzzle'], board)['valid']:
                    raise ValueError('Retry outcome disagrees with independent verifier')
                records.append({'puzzle_id': row['puzzle_id'], 'seed': seed, 'retry_codes': codes[0].cpu().tolist(),
                                'retry_board': board, 'retry_valid': valid, 'elapsed_ms': measured.elapsed_ms})
            torch.cuda.synchronize()
        if (start+len(batch)) % 400 == 0 or start+len(batch) == len(rows):
            print(f'{policy}: {start+len(batch)}/{len(rows)}', flush=True)
    payload = ''.join(json.dumps(r, separators=(',', ':'))+'\n' for r in records).encode()
    with ledger.operation(f'retain {policy} outcomes', feature_bytes=len(payload)):
        raw.parent.mkdir(parents=True, exist_ok=True)
        with raw.open('xb') as stream:
            stream.write(payload)
    statistics = recovery_statistics(np.array([r['y'] for r in rows]), np.array([r['alert'] for r in rows]),
                    np.array([r['retry_valid'] for r in records]), [r['puzzle_id'] for r in rows],
                    [r['elapsed_ms'] for r in records], timing, p)
    result = {'policy': policy, 'statistics': statistics, 'raw_file': raw.relative_to(root).as_posix(),
              'raw_sha256': sha256_file(raw), 'raw_bytes': len(payload)}
    write_json(root/BASE/f'{policy}.json', result)
    return result

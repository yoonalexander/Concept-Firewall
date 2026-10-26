"""Bounded, saved-record recoverability exploration. No inference dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import os
import platform
import subprocess
import threading
import time

import numpy as np

STUDY = 'recoverability-exploration-v1'
MODELS = ('input_logistic', 'decoded_logistic', 'combined_logistic', 'combined_histogram')
DECODED_NAMES = tuple(sorted('decoded.'+s for s in ('filled_cells', 'clue_violations', 'row_conflicts', 'column_conflicts', 'box_conflicts', 'malformed', 'complete', 'current_valid')))
CONFIDENCE_NAMES = ('mean_normalized_entropy', 'max_normalized_entropy', 'mean_top_two_probability_margin', 'minimum_top_two_probability_margin', 'mean_selected_code_log_probability', 'minimum_selected_code_log_probability')
INPUT_NAMES = ('clue_count', 'row_clue_min', 'row_clue_max', 'column_clue_min', 'column_clue_max')
FEATURE_NAMES = DECODED_NAMES + CONFIDENCE_NAMES + INPUT_NAMES + ('prefix_entropy', 'prefix_unique_fraction')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def key(value):
    return hashlib.sha256(f'{STUDY}:{value}'.encode()).hexdigest()


@dataclass(frozen=True)
class Decision:
    """Explicit whitelist; neither outcome nor suffix can enter the extractor."""
    puzzle: str
    puzzle_id: str
    prefix: tuple[int, ...]
    current_board: str
    confidence: tuple[float, ...]

    @classmethod
    def from_saved(cls, row):
        return cls(row['puzzle'], row['puzzle_id'], tuple(row['prefix']), row['current_board'], tuple(row['features'][8:]))


def features(record):
    from .schema import LevelState, puzzle_identity
    from .representations import extract_features
    if type(record) is not Decision:
        raise TypeError('Exact Decision object required')
    if len(record.prefix) != 35 or any(type(c) is not int or not 0 <= c < 16 for c in record.prefix):
        raise ValueError('Only level-6 prefix codes allowed')
    if len(record.confidence) != 6 or record.puzzle_id != puzzle_identity(record.puzzle):
        raise ValueError('Invalid decision boundary')
    pieces, offset = [], 0
    for length in (1, 2, 4, 6, 9, 13):
        pieces.append(record.prefix[offset:offset+length])
        offset += length
    state = LevelState('recoverability', record.puzzle_id, 'recoverability', 6, tuple(pieces), record.current_board)
    f = extract_features(state, record.puzzle)
    cells = np.array([int(c) for c in record.puzzle]).reshape(9, 9) != 0
    inp = (cells.sum(), cells.sum(1).min(), cells.sum(1).max(), cells.sum(0).min(), cells.sum(0).max())
    x = np.array([f[n] for n in DECODED_NAMES]+list(record.confidence)+list(inp)+[f['codes.entropy_bits'], f['codes.unique_fraction']], dtype=float)
    if x.shape != (21,) or not np.isfinite(x).all():
        raise ValueError('Invalid feature vector')
    return x


def fold_ids(groups, n_folds=5):
    ordered = sorted(set(groups), key=key)
    mapping = {g: i % n_folds for i, g in enumerate(ordered)}
    return np.array([mapping[g] for g in groups])


def allocate(scores, folds, ids, budget):
    """Exact largest-remainder fold quotas; no cross-fit score calibration."""
    scores = np.asarray(scores)
    if not 0 <= budget <= len(scores) or not np.isfinite(scores).all():
        raise ValueError('Invalid allocation')
    labels, counts = np.unique(folds, return_counts=True)
    ideal = counts*budget/len(scores)
    quotas = np.floor(ideal).astype(int)
    extra = budget-int(quotas.sum())
    for j in sorted(range(len(labels)), key=lambda j: (-(ideal[j]-quotas[j]), int(labels[j])))[:extra]:
        quotas[j] += 1
    result = np.zeros(len(scores), dtype=bool)
    for f, quota in zip(labels, quotas):
        indices = np.flatnonzero(folds == f)
        order = sorted(indices, key=lambda i: (-scores[i], key(ids[i])))
        result[order[:quota]] = True
    assert int(result.sum()) == budget
    return result


class Ledger:
    """Durable attempted-fit charges and a process CPU/wall watchdog."""
    def __init__(self, path, protocol_hash, limits):
        self.path, self.limits = Path(path), limits
        if self.path.exists():
            raise ValueError('Analysis already attempted; refusing repeated fits')
        self.started, self.cpu_start = time.monotonic(), time.process_time()
        self.lock = threading.RLock()
        self.done = threading.Event()
        self.data = {'study_id': STUDY, 'status': 'running', 'protocol_sha256': protocol_hash,
                     'limits': limits, 'fit_jobs': 0, 'cpu_seconds': 0, 'wall_seconds': 0,
                     'new_model_outputs': 0, 'paid_compute': 0, 'events': []}
        self.save()
        threading.Thread(target=self.watch, daemon=True).start()

    def save(self):
        with self.lock:
            self.data.update(cpu_seconds=time.process_time()-self.cpu_start, wall_seconds=time.monotonic()-self.started)
            write(self.path, self.data)

    def check(self):
        if time.process_time()-self.cpu_start >= self.limits['cpu_seconds'] or time.monotonic()-self.started >= self.limits['wall_seconds']:
            raise RuntimeError('Frozen resource limit exhausted')

    def watch(self):
        while not self.done.wait(.2):
            try:
                self.check()
            except RuntimeError:
                with self.lock:
                    self.data['status'] = 'resource_limit_exhausted'
                    self.save()
                os._exit(124)

    def begin_fit(self, action, family, fold):
        self.check()
        if self.data['fit_jobs'] >= self.limits['fit_jobs']:
            raise RuntimeError('Frozen fit-count limit exhausted')
        self.data['fit_jobs'] += 1
        event = {'action': action, 'model': family, 'fold': int(fold), 'status': 'attempted'}
        self.data['events'].append(event)
        self.save()
        return event

    def finish(self, status):
        self.done.set()
        self.data['status'] = status
        self.save()


def estimator(family, seed):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    if family == 'combined_histogram':
        return HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=7, min_samples_leaf=30,
                    l2_regularization=10, max_bins=32, learning_rate=.1, early_stopping=False, random_state=seed)
    return make_pipeline(StandardScaler(), LogisticRegression(C=.1, solver='lbfgs', max_iter=1000, random_state=seed))


def columns(family):
    return slice(14, 19) if family == 'input_logistic' else slice(0, 14) if family == 'decoded_logistic' else slice(None)


def oof(x, target, groups, folds, family, action, ledger, seed, factory=estimator):
    scores = np.full(len(target), np.nan)
    audit = []
    for f in sorted(set(folds)):
        train, test = folds != f, folds == f
        if set(groups[train]) & set(groups[test]):
            raise ValueError('Puzzle group crossed folds')
        if len(np.unique(target[train])) != 2:
            raise ValueError('Training fold lacks a target class')
        event = ledger.begin_fit(action, family, f)
        start = time.process_time()
        try:
            model = factory(family, seed)
            model.fit(x[train, columns(family)], target[train])
            scores[test] = model.predict_proba(x[test, columns(family)])[:, 1]
            event['status'] = 'completed'
            audit.append({'fold': int(f), 'train_rows': int(train.sum()), 'test_rows': int(test.sum()),
                          'train_rescues': int(target[train].sum()), 'test_rescues': int(target[test].sum()),
                          'disjoint_groups': True,
                          'training_mean': getattr(getattr(model, 'named_steps', {}).get('standardscaler'), 'mean_', np.array([])).tolist()})
        except Exception:
            event['status'] = 'failed'
            raise
        finally:
            event['cpu_seconds'] = time.process_time()-start
            ledger.save()
        ledger.check()
    if not np.isfinite(scores).all():
        raise ValueError('Incomplete OOF predictions')
    return scores, audit


def check_sources(source, inventory):
    for name, item in inventory['files'].items():
        if digest(source/name) != item['sha256'] or (source/name).stat().st_size != item['bytes']:
            raise ValueError('Protected source changed: '+name)


def load_table(source, inventory, protocol):
    """Audit labels separately, then project rows into strict Decision records."""
    from .diagnostics import independent_inspection
    from .sudoku_labels import validate_sudoku
    check_sources(source, inventory)
    base = source/'results/continuation'
    rows = [json.loads(line) for line in (base/'raw/confirmation.jsonl').read_text().splitlines()]
    manifest = read(source/'results/v2/contracts/generator-signals-v1-data.json')['partitions']['confirmation']
    ids = [r['puzzle_id'] for r in rows]
    groups = [r['group'] for r in rows]
    if ids != manifest['puzzle_ids'] or groups != manifest['groups'] or len(set(ids)) != len(ids):
        raise ValueError('Identity/group manifest mismatch')
    x = np.array([features(Decision.from_saved(row)) for row in rows])
    np.testing.assert_allclose(x[:, :14], [r['features'] for r in rows], atol=1e-12, rtol=0)
    probe = read(base/'probe.json')
    failure_scores = ((x[:, :14]-probe['mean'])/probe['scale'])@probe['coefficient']+probe['intercept']
    np.testing.assert_allclose(failure_scores, [r['score'] for r in rows], atol=1e-10, rtol=0)
    failures = []
    for row in rows:
        valid = independent_inspection(row['puzzle'], row['final_board'])['valid']
        if valid != validate_sudoku(row['puzzle'], row['final_board']).is_valid or int(not valid) != row['y']:
            raise ValueError('Original verifier mismatch')
        failures.append(not valid)
    fail = np.array(failures)
    targets, latencies = {}, {}
    for action in protocol['actions']:
        rr = [json.loads(line) for line in (base/'raw'/f'{action}.jsonl').read_text().splitlines()]
        if [r['puzzle_id'] for r in rr] != ids:
            raise ValueError('Misaligned retry records')
        valid = []
        for row, retry in zip(rows, rr):
            v = independent_inspection(row['puzzle'], retry['retry_board'])['valid']
            if v != validate_sudoku(row['puzzle'], retry['retry_board']).is_valid or v != retry['retry_valid']:
                raise ValueError('Retry verifier mismatch')
            valid.append(v)
        targets[action] = np.array(valid, dtype=int)[fail]
        latencies[action] = np.array([r['elapsed_ms'] for r in rr], dtype=float)
        if not np.isfinite(latencies[action]).all() or (latencies[action] <= 0).any():
            raise ValueError('Invalid saved latency')
    ids, groups = np.array(ids), np.array(groups)
    folds = fold_ids(groups, protocol['folds']['count'])
    controls = {'hash_random': np.array([-int(key(i)[:12], 16) for i in ids], dtype=float),
                'failure_risk_high': failure_scores, 'failure_risk_low': -failure_scores,
                'clues_high': x[:, 14],
                'current_conflicts_low': -sum(x[:, DECODED_NAMES.index('decoded.'+name)] for name in ('row_conflicts', 'column_conflicts', 'box_conflicts')),
                'entropy_low': -x[:, 8]}
    return rows, x[fail], fail, ids[fail], groups[fail], folds[fail], controls, targets, latencies


def group_draws(groups, draws, seed):
    labels, inverse = np.unique(groups, return_inverse=True)
    weights = np.random.default_rng(seed).multinomial(len(labels), np.ones(len(labels))/len(labels), size=draws).astype(float)
    return weights, inverse


def contributions(weights, inverse, values):
    values = np.asarray(values)
    if values.ndim == 1:
        values = values[:, None]
    grouped = np.zeros((weights.shape[1], values.shape[1]))
    np.add.at(grouped, inverse, values)
    return weights@grouped


def interval(values, level=.95):
    return np.quantile(values, [(1-level)/2, 1-(1-level)/2]).tolist()


def evaluate_policy(scores, target, folds, ids, budget, n, full_fail, weights, inverse, fail_indices, slot_ms, overhead, monitor, boot_overhead):
    selected = allocate(scores, folds, ids, budget)
    rescues = int(target[selected].sum())
    failures, total = len(target), int(target.sum())
    cost_slots = min(failures, max(0, math.floor(budget+n*overhead/slot_ms+1e-10)))
    own_slots = budget if monitor else cost_slots
    service_selected = allocate(scores, folds, ids, own_slots)
    service_rescues = int(target[service_selected].sum())
    full_values = np.zeros((n, 5))
    full_values[:, 0] = full_fail
    full_values[fail_indices, 1] = target
    full_values[fail_indices, 2] = selected
    full_values[fail_indices, 3] = selected*target
    full_values[fail_indices, 4] = service_selected*target
    sampled = contributions(weights, inverse, full_values)
    fs, ts, ms, rs, srs = sampled.T
    ns = contributions(weights, inverse, np.ones(n))[:, 0]
    expected = ms*ts/np.maximum(fs, 1)
    delta = rs-expected
    # Cost comparison uses each resampled selection count and cohort size.
    bs = np.minimum(fs, np.maximum(0, np.floor(ms+ns*overhead/slot_ms+1e-10)))
    service_delta = srs-bs*ts/np.maximum(fs, 1)
    timing_slots = np.minimum(failures, np.maximum(0, np.floor(budget+n*boot_overhead/slot_ms+1e-10)))
    return {'budget': budget, 'rescues': rescues, 'rescues_per_retry': rescues/budget,
            'uniform_expected': budget*total/failures, 'gain_rescues': rescues-budget*total/failures,
            'gain_accuracy_pp': 100*(rescues-budget*total/failures)/n,
            'gain_rescues_95': interval(delta), 'gain_rescues_97_5': interval(delta, .975),
            'gain_accuracy_pp_95': interval(100*delta/np.maximum(ns, 1)),
            'fold_rescues': [int((selected*(folds == f)*target).sum()) for f in range(5)],
            'service': {'monitor_charged': monitor, 'policy_slots': own_slots, 'random_slots': cost_slots,
                        'policy_rescues': service_rescues, 'uniform_expected': cost_slots*total/failures,
                        'gain_rescues': service_rescues-cost_slots*total/failures,
                        'gain_rescues_95': interval(service_delta), 'envelope_ms': n*(0)+budget*slot_ms+n*overhead,
                        'timing_only_gain_rescues_95': interval(service_rescues-timing_slots*total/failures),
                        'additional_scorer_break_even_ms_per_puzzle': (service_rescues*failures/max(total, 1)-cost_slots)*slot_ms/n},
            '_selected': selected}


def run(source, root):
    import sklearn
    from sklearn.metrics import roc_auc_score, average_precision_score
    from scipy.stats import hypergeom
    from threadpoolctl import threadpool_limits
    protocol_path = root/'configs/recoverability_analysis.json'
    p = read(protocol_path)
    out = root/'results/recoverability'
    inventory = read(out/'inventory.json')
    ledger = Ledger(out/'ledger.json', digest(protocol_path), p['limits'])
    try:
        with threadpool_limits(limits=1):
            rows, x, fail, ids, groups, folds, full_controls, targets, latencies = load_table(source, inventory, p)
            n = len(rows)
            fi = np.flatnonzero(fail)
            weights, inverse = group_draws(np.array([r['group'] for r in rows]), p['uncertainty']['draws'], p['seed'])
            timing = read(source/'results/continuation/timing.json')
            pairs = timing['pairs']
            plain = np.mean([t['plain_ms'] for t in pairs])
            monitored = np.mean([t['monitored_ms'] for t in pairs])
            overhead = monitored-plain
            rng = np.random.default_rng(p['seed'])
            pair_diff = np.array([t['monitored_ms']-t['plain_ms'] for t in pairs])
            boot_overhead = pair_diff[rng.integers(len(pairs), size=(p['uncertainty']['draws'], len(pairs)))].mean(1)
            results = {'study_id': STUDY, 'protocol_sha256': digest(protocol_path), 'inventory_sha256': digest(out/'inventory.json'),
                       'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                       'all_cohorts_exposed': True, 'independent_confirmation': False, 'puzzles': n,
                       'original_failures': len(x), 'features': list(FEATURE_NAMES), 'actions': {},
                       'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
                       'timing': {'plain_mean_ms': plain, 'monitored_mean_ms': monitored, 'overhead_ms': overhead,
                                  'overhead_95': interval(boot_overhead), 'new_scorer_latency_measured': False}}
            predictions = []
            for action in p['actions']:
                target = targets[action]
                score_map = {k: v[fail] for k, v in full_controls.items()}
                audits = {}
                for family in MODELS:
                    score_map[family], audits[family] = oof(x, target, groups, folds, family, action, ledger, p['seed'])
                slot = float(latencies[action].max())
                action_result = {'potential_rescues': int(target.sum()), 'prevalence': float(target.mean()), 'models': {},
                                 'fit_audit': audits, 'retry_slot_ms': slot,
                                 'original_confidence_alert_rescues': int(sum(t*r['alert'] for t, r in zip(target, np.array(rows, dtype=object)[fail])))}
                for name, scores in score_map.items():
                    stats = {'auroc': float(roc_auc_score(target, scores)), 'average_precision': float(average_precision_score(target, scores)), 'budgets': []}
                    for budget in p['budgets']:
                        result = evaluate_policy(scores, target, folds, ids, budget, n, fail, weights, inverse, fi,
                                                 slot, overhead, name not in ('hash_random', 'clues_high', 'input_logistic'), boot_overhead)
                        result.pop('_selected')
                        result['uniform_allocation_95_range'] = hypergeom.ppf([.025, .975], len(target), int(target.sum()), budget).tolist()
                        result['service']['envelope_ms'] += n*plain
                        stats['budgets'].append(result)
                    action_result['models'][name] = stats
                action_result['fold_target_rates'] = [
                    {'fold': f, 'failures': int((folds == f).sum()), 'rescues': int(target[folds == f].sum()),
                     'rate': float(target[folds == f].mean())} for f in range(5)]
                action_result['primary_paired_controls'] = {}
                for budget in p['budgets']:
                    primary_mask = allocate(score_map['combined_logistic'], folds, ids, budget)
                    comparisons = {}
                    for name, scores in score_map.items():
                        if name in MODELS and name != 'input_logistic':
                            continue
                        control_mask = allocate(scores, folds, ids, budget)
                        row_delta = np.zeros(n)
                        row_delta[fi] = (primary_mask.astype(int)-control_mask.astype(int))*target
                        boot_delta = contributions(weights, inverse, row_delta)[:, 0]
                        comparisons[name] = {'gain_rescues': int(row_delta.sum()), 'gain_rescues_95': interval(boot_delta)}
                    action_result['primary_paired_controls'][str(budget)] = comparisons
                primary = action_result['models']['combined_logistic']['budgets'][-1]
                controls = [v['budgets'][-1]['rescues'] for k, v in action_result['models'].items() if k not in MODELS or k == 'input_logistic']
                conditions = {'gain_at_least_8_rescues': primary['gain_rescues'] >= 8,
                              'two_action_interval_lower_positive': primary['gain_rescues_97_5'][0] > 0,
                              'positive_service_gain': primary['service']['gain_rescues'] > 0,
                              'beats_all_cheap_controls': primary['rescues'] > max(controls)}
                decision = 'supports_proposing_independent_study' if all(conditions.values()) else 'reject_advancement' if primary['gain_rescues_97_5'][1] < 8 else 'inconclusive_no_go'
                action_result.update(decision=decision, conditions=conditions)
                results['actions'][action] = action_result
                for i in range(len(ids)):
                    predictions.append({'puzzle_id': str(ids[i]), 'group': str(groups[i]), 'fold': int(folds[i]), 'action': action,
                                        'rescued': int(target[i]), 'scores': {k: float(v[i]) for k, v in score_map.items()}})
                print(action, decision, 'primary rescues:', primary['rescues'], flush=True)
            check_sources(source, inventory)
            results['protected_sources_unchanged'] = True
            ledger.check()
            write(out/'results.json', results)
            (out/'oof_predictions.jsonl').write_text(''.join(json.dumps(row, allow_nan=False)+'\n' for row in predictions), encoding='utf-8')
            write(out/'replay_manifest.json', {'protocol_sha256': digest(protocol_path), 'inventory_sha256': digest(out/'inventory.json'),
                'results_sha256': digest(out/'results.json'), 'predictions_sha256': digest(out/'oof_predictions.jsonl'),
                'implementation_sha256': digest(Path(__file__)), 'source_root': str(source),
                'command': 'python scripts/analyze_recoverability.py --source-root SOURCE_CHECKOUT',
                'research_fits': ledger.data['fit_jobs'], 'protected_sources_unchanged': True})
        ledger.finish('completed')
    except BaseException:
        ledger.finish('failed')
        raise

"""Fixed-probe allocation follow-on, separate from the closed V2 detector gate."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from .artifacts import sha256_file, verified_artifacts
from .decision_value import allocation_summary, portable_scores
from .provenance import new_manifest, require_upstream, save_manifest
from .v2_data import DATA_MANIFEST, load_partition
from .v2_protocol import BudgetLedger, write_json

BASE = Path('results/continuation')
PROTOCOL = Path('configs/confidence_allocation.json')
PARENT = Path('results/manifests/20261025T030127575557Z-v2-study.json')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def freeze(root):
    p = read_json(root/PROTOCOL)
    target = root/BASE/'frozen.json'
    if target.exists():
        require_frozen(root)
        return target
    parent = read_json(root/PARENT)
    probe = parent['models']['decoded_confidence']
    if sha256_file(root/probe['file']) != probe['sha256']:
        raise ValueError('Saved probe changed')
    copied = root/BASE/'probe.json'
    copied.write_bytes((root/probe['file']).read_bytes())
    if sha256_file(copied) != probe['sha256']:
        raise ValueError('Frozen probe copy differs')
    require_upstream(root)
    contract = {'study_id': p['study_id'], 'protocol_sha256': sha256_file(root/PROTOCOL),
                'parent_manifest_sha256': sha256_file(root/PARENT),
                'data_manifest_sha256': sha256_file(root/DATA_MANIFEST),
                'artifact_sha256': verified_artifacts(root),
                'probe_sha256': probe['sha256'],
                'old_ledger_sha256': sha256_file(root/'results/v2/runtime/generator-signals-v1.json'),
                'confirmation_previously_generated': False,
                'old_study_status': 'closed; original gate failed; not amended'}
    write_json(target, contract)
    return target


def require_frozen(root):
    p, f = read_json(root/PROTOCOL), read_json(root/BASE/'frozen.json')
    checks = {root/PROTOCOL: f['protocol_sha256'], root/PARENT: f['parent_manifest_sha256'],
              root/DATA_MANIFEST: f['data_manifest_sha256'], root/BASE/'probe.json': f['probe_sha256'],
              root/'results/v2/runtime/generator-signals-v1.json': f['old_ledger_sha256']}
    for path, digest in checks.items():
        if sha256_file(path) != digest:
            raise ValueError(f'Frozen artifact changed: {path}')
    if p['study_id'] != 'confidence-allocation-v1' or p['fits'] != 0:
        raise ValueError('Unexpected study or nonzero fit allowance')
    return p, f


def wilson_upper(k, n, z=1.6448536269514722):
    if not 0 <= k <= n or n <= 0:
        raise ValueError('Invalid binomial counts')
    rate = k/n
    return (rate+z*z/(2*n)+z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n)))/(1+z*z/n)


def confirmation_statistics(y, alerts, protocol):
    import numpy as np
    from scipy.stats import hypergeom
    s = allocation_summary(y, alerts)
    n, tp, fp = s['puzzles'], s['true_positives'], s['false_positives']
    counts = np.array([tp, fp, s['failures']-tp, s['successes']-fp])
    draws = np.random.default_rng(protocol['bootstrap_seed']).multinomial(n, counts/n, protocol['bootstrap_draws'])
    advantage = draws[:, 0]/n - (draws[:, 0]+draws[:, 1])*(draws[:, 0]+draws[:, 2])/(n*n)
    lower = float(np.quantile(advantage, .05))
    s.update(allocation_capacity_one_sided_95_lower=lower,
             enrichment_exact_p=float(hypergeom.sf(tp-1, n, s['failures'], s['alerts'])),
             fpr_one_sided_95_upper=wilson_upper(fp, s['successes']))
    gate = protocol['confirmation_gate']
    conditions = {'fixed_cohort_complete': n == protocol['confirmation_puzzles'],
                  'outcome_counts': min(s['failures'], s['successes']) >= gate['minimum_per_class'],
                  'bounded_alert_budget': s['alert_fraction'] <= gate['maximum_alert_fraction'],
                  'false_alarm_bound': s['fpr_one_sided_95_upper'] <= gate['maximum_fpr_upper'],
                  'potential_value_floor': s['perfect_retry_advantage_over_random_all'] >= gate['minimum_capacity_advantage'],
                  'positive_allocation_capacity_lower_bound': lower > 0}
    return {'metrics': s, 'conditions': conditions, 'gate_passed': all(conditions.values()),
            'claim': 'Fixed alerts enrich baseline failures at limited coverage; recovery and cost advantage remain untested'}


class ConfidenceMonitor:
    """Score actual current-prefix boards/logits before any future level runs."""
    def __init__(self, adapter, record, level=6):
        self.adapter, self.record, self.level = adapter, record, level
        if not adapter.generator.query_level0 or adapter.generator.l0_ar or adapter.generation_settings.cfg_scale:
            raise ValueError('Only the pinned parallel non-CFG path is supported')
        if not 1 <= level <= len(adapter.levels):
            raise ValueError('Invalid observation level')

    def generate(self, context, puzzles, callback=None):
        import numpy as np
        import torch
        from .probes import feature_vector
        from .representations import extract_features
        from .schema import LevelState, puzzle_identity
        from .spatial import reconstruct_prefix
        from .v2_observer import confidence_summary
        model, level = self.adapter.generator, self.level
        if '_sample_level' in model.__dict__:
            raise ValueError('Generator already has a sampling override')
        if len(puzzles) != len(context):
            raise ValueError('Puzzle/context batch differs')
        original = model._sample_level
        pieces, records = [], []
        logits_at_boundary = None

        def hook(_module, _inputs, logits):
            nonlocal logits_at_boundary
            if len(pieces) != level-1 or logits_at_boundary is not None:
                raise ValueError('Unexpected observation head order')
            logits_at_boundary = logits.detach()

        def sample(logits, *args, **kwargs):
            selected = original(logits, *args, **kwargs)
            index = len(pieces)
            pieces.append(selected.detach().clone() if index < level else None)
            if index+1 == level:
                if logits_at_boundary is None:
                    raise ValueError('Missing boundary logits')
                confidence = confidence_summary(torch.log_softmax(logits_at_boundary.float(), -1), selected).cpu().numpy()
                prefix = torch.cat(pieces, dim=1)
                current = self.adapter._decode_latent(reconstruct_prefix(self.adapter.tokenizer.vqvae.vq, prefix, level))
                raw = [p.cpu().tolist() for p in pieces]
                features = []
                for i, puzzle in enumerate(puzzles):
                    codes = tuple(tuple(p[i]) for p in raw)
                    state = LevelState('allocation', puzzle_identity(puzzle), str(i), level, codes, current[i])
                    decoded = feature_vector(extract_features(state, puzzle), codes, 'decoded')[1]
                    features.append(list(decoded)+confidence[i].tolist())
                scores = portable_scores(self.record, np.asarray(features))
                for i, score in enumerate(scores):
                    records.append({'score': float(score), 'alert': bool(score > self.record['threshold']),
                                    'prefix': prefix[i].cpu().tolist(), 'current_board': current[i],
                                    'features': features[i]})
                if callback:
                    callback(tuple(records))
            return selected

        handle = model.lm_heads[level-1].register_forward_hook(hook)
        model._sample_level = sample
        try:
            with torch.no_grad():
                codes = self.adapter.generate(context)
            if len(records) != len(context) or len(pieces) != len(self.adapter.levels):
                raise ValueError('Observation was not delivered exactly once')
            return codes, records
        finally:
            handle.remove()
            del model._sample_level


def run_confirmation(root):
    import numpy as np
    import torch
    from .diagnostics import independent_inspection
    from .sudoku_labels import validate_sudoku
    from .upstream_adapter import NCMAdapter
    from .v2_training import encode_puzzle
    p, frozen = require_frozen(root)
    target = root/BASE/'confirmation.json'
    if target.exists():
        raise ValueError('Confirmation already attempted; refusing an outcome-driven repeat')
    require_upstream(root)
    if verified_artifacts(root) != frozen['artifact_sha256']:
        raise ValueError('Official artifacts changed')
    ledger = BudgetLedger(root/BASE/'runtime/ledger.json', frozen['protocol_sha256'], p['limits'])
    manifest = new_manifest(root, 'allocation-confirmation', {'protocol_sha256': frozen['protocol_sha256'],
                             'old_study_reopened': False, 'new_fits': 0})
    manifest['command'] = [sys.executable, str(root/'scripts/confidence_allocation.py'), 'confirm']
    save_manifest(root, manifest)
    write_json(target, {'status': 'running', 'run_manifest': manifest['run_id']})
    try:
        with ledger.operation('load confirmation models', timed_resource='gpu_seconds'):
            adapter = NCMAdapter.load(root/'third_party/ncm', root/'third_party/ncm/config/eval/sudoku-hard.yaml', root/'artifacts/sudoku-hard', device='cuda')
            monitor = ConfidenceMonitor(adapter, read_json(root/BASE/'probe.json'), p['level'])
            torch.cuda.synchronize()
        # Check the optimized confidence-only path against retained development
        # features and plain generation before consuming any held-out outcomes.
        cap = read_json(root/PARENT)['captures']['calibration']
        if sha256_file(root/cap['file']) != cap['sha256']:
            raise ValueError('Saved calibration capture changed')
        development = load_partition(root, 'calibration')[:8]
        with ledger.operation('eight exposed calibration equivalence checks', timed_resource='gpu_seconds', model_puzzles=16):
            context = adapter.prepare_context([encode_puzzle(row['puzzle']) for row in development])
            control = adapter.generate(context)
            observed, obs = monitor.generate(context, [row['puzzle'] for row in development])
            if not torch.equal(control, observed):
                raise ValueError('Live confidence monitor changed generation')
            with np.load(root/cap['file'], allow_pickle=False) as saved:
                np.testing.assert_allclose([r['features'] for r in obs], saved['decoded_confidence'][:8], rtol=0, atol=1e-8)
            torch.cuda.synchronize()
        manifest['preflight'] = {'exposed_calibration_puzzles': 8, 'all_codes_equal': True, 'all_features_match_saved': True}
        save_manifest(root, manifest)
        rows = load_partition(root, 'confirmation', confirmation_authorized=True)
        records = []
        for start in range(0, len(rows), p['batch_size']):
            batch = rows[start:start+p['batch_size']]
            with ledger.operation(f'confirmation batch {start}', timed_resource='gpu_seconds', model_puzzles=len(batch)):
                context = adapter.prepare_context([encode_puzzle(row['puzzle']) for row in batch])
                codes, obs = monitor.generate(context, [row['puzzle'] for row in batch])
                final = adapter.decode_final(codes)
                for row, observation, code, board in zip(batch, obs, codes.cpu().tolist(), final):
                    valid = validate_sudoku(row['puzzle'], board).is_valid
                    if valid != independent_inspection(row['puzzle'], board)['valid']:
                        raise ValueError('Independent outcome check disagrees')
                    records.append({**row, **observation, 'codes': code, 'final_board': board, 'y': int(not valid)})
                torch.cuda.synchronize()
            if (start+len(batch)) % 400 == 0:
                print(f'Fixed confirmation: {start+len(batch)}/{len(rows)}', flush=True)
        raw = root/BASE/'raw/confirmation.jsonl'
        payload = ''.join(json.dumps(r, separators=(',', ':'))+'\n' for r in records).encode()
        with ledger.operation('retain confirmation', feature_bytes=len(payload)):
            raw.parent.mkdir(parents=True, exist_ok=True)
            with raw.open('xb') as stream:
                stream.write(payload)
        result = confirmation_statistics(np.array([r['y'] for r in records]), np.array([r['alert'] for r in records]), p)
        result.update(status='completed', study_id=p['study_id'], raw_file=raw.relative_to(root).as_posix(),
                      raw_sha256=sha256_file(raw), protocol_sha256=frozen['protocol_sha256'],
                      original_40_percent_recall_gate_still_failed=True, new_fits=0,
                      confirmation_consumed=True, budget=ledger.snapshot(), run_manifest=manifest['run_id'])
        write_json(target, result)
        manifest.update(status='passed', result_file=target.relative_to(root).as_posix(), result_sha256=sha256_file(target),
                        allocation_gate_passed=result['gate_passed'], budget=ledger.snapshot())
    except BaseException as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}', budget=ledger.snapshot())
        write_json(target, {'status': 'failed', 'error': manifest['error'], 'run_manifest': manifest['run_id']})
        save_manifest(root, manifest)
        raise
    save_manifest(root, manifest)
    return target

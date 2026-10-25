import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

import numpy as np

from concept_firewall.allocation_recovery import BASE, identity_seed, recovery_statistics, retry_codes, run_recovery

ROOT = Path(__file__).resolve().parents[1]


class RecoveryStatisticsTests(unittest.TestCase):
    def test_consumed_recovery_refuses_before_any_model_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/BASE).mkdir(parents=True)
            (root/BASE/'recovery.json').write_text('{"status":"completed"}')
            with patch('concept_firewall.allocation_recovery.require_frozen', return_value=({}, {})), \
                 patch('concept_firewall.upstream_adapter.NCMAdapter.load') as load:
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    run_recovery(root)
                load.assert_not_called()

    def test_verifier_baseline_and_monitoring_cost_can_defeat_failure_enrichment(self):
        p = json.loads((ROOT/'configs/confidence_allocation.json').read_text())
        y = np.array([1]*1000+[0]*600)
        alerts = np.array([True]*220+[False]*780+[True]*30+[False]*570)
        # Recovery is equally available for every failure: verifier-first wins.
        result = recovery_statistics(y, alerts, np.ones(1600, dtype=bool), [str(i) for i in range(1600)],
                                     [10]*1600, {'plain_mean_ms': 10, 'monitored_mean_ms': 12}, p)
        self.assertEqual(result['confidence_recovered'], 220)
        self.assertEqual(result['verifier_first']['expected_recovered'], 250)
        self.assertFalse(result['gate_passed'])
        self.assertEqual(result['service_budget']['verifier_retry_slots'], 570)
        # Risk targeting helps only when actual recoveries concentrate there.
        retry = alerts & (y == 1)
        result = recovery_statistics(y, alerts, retry, [str(i) for i in range(1600)], [10]*1600,
                                     {'plain_mean_ms': 10, 'monitored_mean_ms': 10}, p)
        self.assertTrue(result['gate_passed'])
        self.assertEqual(result['confidence_solved'], 820)
        self.assertTrue(result['unchanged_successes_preserved'])

    def test_identity_rng_not_dependent_on_order(self):
        self.assertEqual(identity_seed('s', 'p', 'a', 1), identity_seed('s', 'p', 'a', 1))
        self.assertNotEqual(identity_seed('s', 'p', 'a', 1), identity_seed('s', 'p', 'b', 1))

    def test_forced_prefix_equivalence_stochastic_repeatability_rng_and_cleanup(self):
        import torch
        import test_baseline_equivalence as tiny
        tiny.TinyUpstreamEquivalenceTests.setUpClass()
        adapter, context = tiny.TinyUpstreamEquivalenceTests.adapter, tiny.TinyUpstreamEquivalenceTests.context
        control = adapter.generate(context)
        prefix = control[:, :3]
        before = torch.random.get_rng_state().clone()
        replay = retry_codes(adapter, context, prefix=prefix, level=2, temperature=0, seed=17)
        self.assertTrue(torch.equal(control, replay))
        a = retry_codes(adapter, context, prefix=prefix, level=2, temperature=.5, seed=17)
        b = retry_codes(adapter, context, prefix=prefix, level=2, temperature=.5, seed=17)
        self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(a[:, :3], prefix))
        self.assertTrue(torch.equal(before, torch.random.get_rng_state()))
        with patch.object(adapter, 'generate', side_effect=RuntimeError('intentional')):
            with self.assertRaisesRegex(RuntimeError, 'intentional'):
                retry_codes(adapter, context, prefix=prefix, level=2, temperature=.5, seed=17)
        self.assertNotIn('_sample_level', adapter.generator.__dict__)

import json
from pathlib import Path
import unittest

import numpy as np

from concept_firewall.confidence_allocation import ConfidenceMonitor, confirmation_statistics, wilson_upper

ROOT = Path(__file__).resolve().parents[1]


class AllocationStatisticsTests(unittest.TestCase):
    def test_enrichment_screen_has_no_recall_redefinition(self):
        p = json.loads((ROOT/'configs/confidence_allocation.json').read_text())
        y = np.array([1]*1000+[0]*600)
        alerts = np.array([True]*220+[False]*780+[True]*30+[False]*570)
        result = confirmation_statistics(y, alerts, p)
        self.assertTrue(result['gate_passed'])
        self.assertLess(result['metrics']['recall'], .4)
        self.assertFalse(confirmation_statistics(y, ~alerts, p)['gate_passed'])
        self.assertGreater(wilson_upper(30, 600), .05)
        with self.assertRaises(ValueError):
            wilson_upper(1, 0)

    def test_live_score_matches_existing_observer_without_using_future(self):
        import torch
        import test_baseline_equivalence as tiny
        from concept_firewall.v2_observer import GeneratorObserver
        tiny.TinyUpstreamEquivalenceTests.setUpClass()
        adapter = tiny.TinyUpstreamEquivalenceTests.adapter
        context = tiny.TinyUpstreamEquivalenceTests.context
        # The board decoder here emits short toy boards; its whitelisted features
        # still have the same dimensionality and malformed-board handling.
        from concept_firewall.probes import feature_vector
        from concept_firewall.schema import LevelState, puzzle_identity
        from concept_firewall.representations import extract_features
        state = LevelState('t', puzzle_identity('0'*81), 't', 2, ((0,), (0, 0)), '')
        width = len(feature_vector(extract_features(state, '0'*81), state.codes_prefix, 'decoded')[1])+6
        record = dict(mean=[0]*width, scale=[1]*width, coefficient=[.1]*width, intercept=0, classes=[0, 1], threshold=0)
        expected, obs = GeneratorObserver(adapter, level=2, projection_dimension=8).generate(context)
        events = []
        handle = adapter.generator.lm_heads[-1].register_forward_hook(lambda m, i, o: events.append('future'))
        try:
            codes, records = ConfidenceMonitor(adapter, record, 2).generate(context, ['0'*81]*2, lambda r: events.append('score'))
        finally:
            handle.remove()
        self.assertEqual(events, ['score', 'future'])
        self.assertTrue(torch.equal(expected, codes))
        np.testing.assert_allclose([r['features'][-6:] for r in records], obs.confidence_by_sample)
        def fail(records):
            raise RuntimeError('failed callback')
        with self.assertRaisesRegex(RuntimeError, 'failed callback'):
            ConfidenceMonitor(adapter, record, 2).generate(context, ['0'*81]*2, fail)
        self.assertNotIn('_sample_level', adapter.generator.__dict__)

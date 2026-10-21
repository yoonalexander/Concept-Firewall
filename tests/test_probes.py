import math
from pathlib import Path
import tempfile
import unittest
from dataclasses import asdict
import json

from concept_firewall.probes import LinearProbe, feature_vector
from concept_firewall.representations import extract_features
from concept_firewall.schema import LevelState, puzzle_identity
from concept_firewall.training import probability_metrics


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.puzzle = "0" * 81
        self.state = LevelState("r", puzzle_identity(self.puzzle), "t", 1, ((2,),), "0" * 81, (2.0, -1.0))
        self.features = dict(extract_features(self.state, self.puzzle))

    def test_whitelist_ignores_outcomes_and_other_representation_families(self):
        names, values = feature_vector(self.features, self.state.codes_prefix, "input")
        changed = dict(self.features, final_valid=1.0, future_secret=88.0)
        changed["latent.component.0000"] = 99999
        self.assertEqual((names, values), feature_vector(changed, self.state.codes_prefix, "input"))
        self.assertEqual(sum(v for k,v in zip(names, values) if k.startswith("input.cell.")), 81)

    def test_portable_probability_matches_logistic_arithmetic(self):
        names, values = feature_vector(self.features, self.state.codes_prefix, "latent")
        probe = LinearProbe("latent", 1, names, (0.0, 0.0), (1.0, 1.0), (.2, .3), .4, 2.0, -.1)
        expected = 1/(1+math.exp(-(-.1 + 2*(.4+.2*values[0]+.3*values[1]))))
        self.assertAlmostEqual(probe.predict_failure_probability(self.state, self.puzzle), expected)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"probe.json"
            path.write_text(json.dumps({"schema_version": 1, **asdict(probe)}))
            self.assertEqual(LinearProbe.load(path), probe)

    def test_single_class_discrimination_is_unavailable(self):
        metrics = probability_metrics([0, 0], [.2, .3], .25)
        self.assertIsNone(metrics["auroc"])
        self.assertIsNone(metrics["average_precision"])
        self.assertIsNone(metrics["recall"])
        self.assertEqual(metrics["fpr"], .5)

    def test_reversed_ranking_and_strict_threshold(self):
        metrics = probability_metrics([0, 1], [.8, .2], .8)
        self.assertEqual(metrics["auroc"], 0)
        self.assertEqual(metrics["fpr"], 0)
        self.assertEqual(metrics["recall"], 0)

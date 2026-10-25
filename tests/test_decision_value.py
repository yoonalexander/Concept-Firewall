import unittest

import numpy as np

from concept_firewall.decision_value import allocation_summary, portable_scores, recovery_scenario


class DecisionValueTests(unittest.TestCase):
    def test_perfect_and_identical_retry_bounds(self):
        s = allocation_summary([1, 1, 0, 0], np.array([True, False, True, False]))
        self.assertEqual(s['perfect_retry_gain_ceiling'], .25)
        self.assertEqual(s['perfect_retry_advantage_over_random_all'], 0)
        self.assertEqual(s['selected_recovery_ratio_needed_vs_verifier_first'], 2)
        identical = recovery_scenario(s, 0, 0, 1)
        self.assertEqual(identical['hypothetical_accuracy_gain'], 0)
        self.assertLess(identical['correct_answers_per_compute'], .5)
        self.assertEqual(recovery_scenario(s, 1, 0, 1)['correct_answers_per_compute'], .5)
        self.assertEqual(recovery_scenario(s, 1, 1, 1)['hypothetical_accuracy_gain'], 0)

    def test_invalid_inputs_and_finite_portable_scores(self):
        with self.assertRaises(ValueError):
            allocation_summary([1, 0], np.array([1, 0]))
        with self.assertRaises(ValueError):
            recovery_scenario({}, -1, 0, 0)
        model = dict(mean=[1], scale=[2], coefficient=[3], intercept=4, classes=[0, 1])
        np.testing.assert_allclose(portable_scores(model, [[3]]), [7])
        with self.assertRaises(ValueError):
            portable_scores({**model, 'scale': [0]}, [[3]])

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from concept_firewall.recoverability_analysis import (
    Decision, features, fold_ids, allocate, Ledger, oof, group_draws, contributions, evaluate_policy)
from concept_firewall.schema import puzzle_identity


class ConstantClassifier(ClassifierMixin, BaseEstimator):
    def fit(self, x, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, x):
        return np.tile([.5, .5], (len(x), 1))


class RecoverabilityTests(unittest.TestCase):
    def test_future_and_outcomes_never_enter_features(self):
        puzzle = '0'*81
        row = {'puzzle': puzzle, 'puzzle_id': puzzle_identity(puzzle), 'prefix': [1]*35,
               'current_board': '0'*81, 'features': [0]*14, 'codes': [8]*322,
               'final_board': '9'*81, 'retry_valid': True, 'y': 1, 'score': 999}
        x = features(Decision.from_saved(row))
        row.update(codes=[15]*322, final_board='1'*81, retry_valid=False, y=0, score=-999)
        np.testing.assert_array_equal(x, features(Decision.from_saved(row)))
        self.assertEqual(x.shape, (21,))
        with self.assertRaises(TypeError):
            features(row)
        row['prefix'].append(2)
        with self.assertRaises(ValueError):
            features(Decision.from_saved(row))

    def test_groups_stay_together_and_assignment_is_order_independent(self):
        groups = ['a', 'b', 'a', 'c', 'd', 'e', 'f', 'b']
        folds = fold_ids(groups)
        self.assertEqual(folds[0], folds[2])
        self.assertEqual(folds[1], folds[-1])
        np.testing.assert_array_equal(folds[::-1], fold_ids(groups[::-1]))

    def test_scaler_is_fit_with_only_training_groups(self):
        groups = np.array([str(i//2) for i in range(40)])
        folds = fold_ids(groups)
        x = np.arange(40*21, dtype=float).reshape(40, 21)
        y = np.arange(40) % 2
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/'ledger.json', 'hash', {'fit_jobs': 5, 'cpu_seconds': 30, 'wall_seconds': 60})
            try:
                _, audit = oof(x, y, groups, folds, 'combined_logistic', 'action', ledger, 42,
                    factory=lambda *_: make_pipeline(StandardScaler(), ConstantClassifier()))
                self.assertEqual(ledger.data['fit_jobs'], 5)
                for record in audit:
                    f = record['fold']
                    np.testing.assert_allclose(record['training_mean'], x[folds != f].mean(0))
                    self.assertTrue(record['disjoint_groups'])
                with self.assertRaisesRegex(RuntimeError, 'fit-count'):
                    ledger.begin_fit('action', 'model', 0)
            finally:
                ledger.finish('test_completed_no_learned_estimator')

    def test_allocation_exact_quotas_and_stable_ties(self):
        ids = np.array([str(i) for i in range(101)])
        folds = np.arange(101) % 5
        scores = np.ones(101)
        for budget in (0, 1, 27, 101):
            selected = allocate(scores, folds, ids, budget)
            self.assertEqual(selected.sum(), budget)
            self.assertLessEqual(max(selected[folds == f].sum() for f in range(5))-
                                 min(selected[folds == f].sum() for f in range(5)), 1)
            np.testing.assert_array_equal(selected[::-1], allocate(scores[::-1], folds[::-1], ids[::-1], budget))

    def test_group_bootstrap_moves_related_records_together(self):
        weights, inverse = group_draws(['a', 'a', 'b'], 20, 7)
        total = contributions(weights, inverse, [1, 1, 0])[:, 0]
        np.testing.assert_array_equal(total, 2*weights[:, 0])

    def test_equal_count_service_slots_and_bootstrap_are_action_specific(self):
        n = 20
        fail = np.array([True]*10+[False]*10)
        folds = np.arange(10) % 5
        ids = np.array([str(i) for i in range(10)])
        target = np.array([1]*5+[0]*5)
        weights, inverse = group_draws(np.array([str(i) for i in range(n)]), 100, 7)
        result = evaluate_policy(np.arange(10)[::-1], target, folds, ids, 5, n, fail, weights, inverse,
                                 np.flatnonzero(fail), 10, 1, True, np.ones(100))
        self.assertEqual(result['rescues'], 5)
        self.assertEqual(result['uniform_expected'], 2.5)
        self.assertEqual(result['service']['random_slots'], 7)
        self.assertEqual(result['service']['policy_slots'], 5)
        self.assertEqual(result['service']['gain_rescues'], 1.5)
        zero = evaluate_policy(np.arange(10)[::-1], np.zeros(10, dtype=int), folds, ids, 5, n, fail,
                               weights, inverse, np.flatnonzero(fail), 10, 1, True, np.ones(100))
        self.assertEqual(zero['rescues'], 0)
        self.assertEqual(zero['gain_rescues_95'], [0, 0])

    def test_failed_fit_is_charged_and_repeated_analysis_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ledger.json'
            ledger = Ledger(path, 'hash', {'fit_jobs': 5, 'cpu_seconds': 30, 'wall_seconds': 60})
            groups = np.array([str(i) for i in range(20)])
            def broken(*_):
                raise RuntimeError('intentional')
            try:
                with self.assertRaisesRegex(RuntimeError, 'intentional'):
                    oof(np.zeros((20, 21)), np.arange(20) % 2, groups, fold_ids(groups),
                        'combined_logistic', 'action', ledger, 42, factory=broken)
                self.assertEqual(ledger.data['fit_jobs'], 1)
                self.assertEqual(ledger.data['events'][0]['status'], 'failed')
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    Ledger(path, 'hash', ledger.limits)
                ledger.cpu_start -= 40
                with self.assertRaisesRegex(RuntimeError, 'resource'):
                    ledger.check()
            finally:
                ledger.finish('test_completed_no_learned_estimator')


if __name__ == '__main__':
    unittest.main()

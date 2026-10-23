import importlib.util
import time
import unittest

from concept_firewall.followup import fit_linear, group_folds, select_linear


AVAILABLE=all(importlib.util.find_spec(name) is not None for name in ("numpy","sklearn"))


@unittest.skipUnless(AVAILABLE,"follow-up fitting tests need optional research dependencies")
class DevelopmentOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        import numpy as np

    def test_duplicate_groups_stay_in_one_fold_independent_of_row_order(self):
        groups=np.asarray([str(i) for i in range(20)]*3)
        assignments=group_folds(groups,4,42)
        for group in set(groups):
            self.assertEqual(len(set(assignments[groups==group])),1)
        reverse=group_folds(groups[::-1],4,42)
        self.assertTrue(np.array_equal(assignments,reverse[::-1]))

    def test_fitted_scaler_and_model_ignore_assessment_features_and_labels(self):
        x=np.random.default_rng(4).normal(size=(80,4))
        y=np.arange(80)%2
        training=np.arange(40)
        first=fit_linear(x,y,training,.01,42)
        changed=x.copy()
        changed[40:]=1e6
        changed_labels=y.copy()
        changed_labels[40:]=1-y[40:]
        second=fit_linear(changed,changed_labels,training,.01,42)
        np.testing.assert_allclose(first.scaler.mean_,x[training].mean(axis=0))
        np.testing.assert_array_equal(first.scaler.mean_,second.scaler.mean_)
        np.testing.assert_array_equal(first.model.coef_,second.model.coef_)

    def test_selection_never_uses_outer_assessment_outcomes(self):
        rng=np.random.default_rng(7)
        x=rng.normal(size=(80,3))
        y=np.arange(80)%2
        training=np.arange(60)
        inner=(training//2)%2
        first=select_linear(x,y,training,inner,[.01,.1],42,time.perf_counter()+30)
        labels=y.copy()
        labels[60:]=1-y[60:]
        second=select_linear(x,labels,training,inner,[.01,.1],42,time.perf_counter()+30)
        self.assertEqual(first.C,second.C)
        self.assertEqual(first.validation_loss,second.validation_loss)
        np.testing.assert_array_equal(first.model.coef_,second.model.coef_)

    def test_expired_budget_stops_selection(self):
        with self.assertRaisesRegex(RuntimeError,"budget"):
            select_linear(np.ones((8,2)),np.arange(8)%2,np.arange(8),np.arange(8)//4,[.01],0,0)

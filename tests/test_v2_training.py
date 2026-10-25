from pathlib import Path
import tempfile
import unittest

import numpy as np

from concept_firewall.v2_protocol import BudgetLedger, load_protocol
from concept_firewall.v2_training import development_gate, encode_puzzle, negative_threshold, operating_metrics, select_family, validation_halves

ROOT=Path(__file__).resolve().parents[1]


class V2TrainingTests(unittest.TestCase):
    def test_threshold_ties_and_false_alarm_budget(self):
        for n in (1,19,20,21,100):
            scores=np.arange(n)
            self.assertLessEqual(float((scores>negative_threshold(scores)).mean()),.05+1e-12)
        self.assertEqual(negative_threshold([1,1,1]),1)
        with self.assertRaises(ValueError):
            negative_threshold([np.nan])

    def test_gate_requires_all_controls_and_practical_targets(self):
        p=load_protocol(ROOT/'configs/v2_study.json')
        candidate={'recall':.5,'fpr':.04}
        self.assertTrue(development_gate(candidate,[{'recall':.2},{'recall':.3}],p))
        self.assertFalse(development_gate(candidate,[{'recall':.49}],p))
        self.assertFalse(development_gate({'recall':.39,'fpr':0},[{'recall':0}],p))
        self.assertFalse(development_gate({'recall':.9,'fpr':.051},[{'recall':0}],p))

    def test_validation_halves_disjoint_and_input_encoding_has_no_solution(self):
        a,b=validation_halves(['a','b','c','d'],'study')
        self.assertFalse(set(a)&set(b))
        self.assertEqual(set(a)|set(b),set(range(4)))
        encoded=encode_puzzle('0'*81)
        self.assertEqual(len(encoded),91)
        self.assertEqual(encoded[0],11)
        self.assertEqual(encoded[-1],11)
        self.assertEqual(encoded.count(10),8)

    def test_scaling_and_coefficients_fit_training_only_and_charge_two_jobs(self):
        rng=np.random.default_rng(7)
        x=rng.normal(size=(80,3)); y=np.tile([0,1],40)
        val_x=rng.normal(100,1,size=(40,3)); val_y=np.tile([0,1],20)
        p=load_protocol(ROOT/'configs/v2_study.json')
        selection=np.arange(20); assessment=np.arange(20,40)
        with tempfile.TemporaryDirectory() as d:
            ledger=BudgetLedger(Path(d)/'ledger.json','test',{'fit_jobs':2,'cpu_fit_seconds':30})
            fit,record=select_family(x,y,val_x,val_y,selection,assessment,p,ledger)
            np.testing.assert_allclose(fit.scaler.mean_,x.mean(0))
            self.assertEqual(ledger.snapshot()['used']['fit_jobs'],2)
            self.assertIn(record['C'],p['fitting']['C'])
            self.assertEqual(operating_metrics(val_y,fit.margins(val_x),999)['recall'],0)

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from concept_firewall.v2_protocol import BudgetExceeded, BudgetLedger, load_protocol, prospective_precision, require_contract, write_json

ROOT=Path(__file__).resolve().parents[1]


class V2ContractTests(unittest.TestCase):
    def test_protocol_has_realistic_prospective_precision_not_model_results(self):
        p=load_protocol(ROOT/'configs/v2_study.json')
        plan=prospective_precision(p)
        self.assertAlmostEqual(plan['expected_failures'],220)
        self.assertGreater(plan['paired_lift_gate_pass_fraction_normal_approximation'],.8)
        self.assertLess(plan['fpr_scenarios']['0.05']['fpr_gate_pass_fraction'],.6)
        self.assertIn('Not joint study power',plan['limits'])

    def test_invalid_fit_accounting_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=json.loads((ROOT/'configs/v2_study.json').read_text())
            p['fitting']['fit_accounting']['cheap_selection']=9
            target=Path(d)/'bad.json'
            write_json(target,p)
            with self.assertRaisesRegex(ValueError,'Fit-job'):
                load_protocol(target)

    def test_amended_protocol_cannot_use_existing_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_json(root/'results/v2/contracts/generator-signals-v1.json',{'status':'frozen','protocol_sha256':'wrong'})
            with self.assertRaisesRegex(ValueError,'Protocol changed'):
                require_contract(root,ROOT/'configs/v2_study.json')


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'ledger.json'
        self.ledger=BudgetLedger(self.path,'frozen',{'fit_jobs':2,'cpu_fit_seconds':10})

    def test_failed_attempt_is_charged_and_survives_reload(self):
        with patch('concept_firewall.v2_protocol.time.perf_counter',side_effect=[1,4]):
            with self.assertRaisesRegex(RuntimeError,'fit failed'):
                with self.ledger.operation('fit',timed_resource='cpu_fit_seconds',fit_jobs=1):
                    raise RuntimeError('fit failed')
        reloaded=BudgetLedger(self.path,'frozen',self.ledger.limits).snapshot()
        self.assertEqual(reloaded['used'],{'fit_jobs':1,'cpu_fit_seconds':3})
        self.assertEqual(reloaded['events'][0]['status'],'failed')

    def test_budget_denial_and_overshoot_cannot_reset_counters(self):
        with self.assertRaises(BudgetExceeded):
            with self.ledger.operation('too many',fit_jobs=3):
                self.fail('operation ran')
        with patch('concept_firewall.v2_protocol.time.perf_counter',side_effect=[0,11]):
            with self.assertRaises(BudgetExceeded):
                with self.ledger.operation('overlong',timed_resource='cpu_fit_seconds'):
                    pass
        with self.assertRaises(BudgetExceeded):
            with self.ledger.operation('retry',fit_jobs=1):
                self.fail('exhausted study ran')
        self.assertEqual(self.ledger.snapshot()['used']['cpu_fit_seconds'],11)

    def test_interrupted_operation_fails_closed_and_foreign_protocol_rejected(self):
        state=self.ledger.snapshot()
        state['active']={'name':'interrupted'}
        write_json(self.path,state)
        with self.assertRaises(BudgetExceeded):
            with self.ledger.operation('new fit',fit_jobs=1):
                self.fail('interrupted work ignored')
        with self.assertRaises(ValueError):
            BudgetLedger(self.path,'changed',self.ledger.limits)

    def test_negative_boolean_nan_and_unknown_charges_rejected(self):
        for charges in ({'fit_jobs':-1},{'fit_jobs':True},{'fit_jobs':float('nan')},{'other':1}):
            with self.subTest(charges=charges), self.assertRaises(ValueError):
                with self.ledger.operation('bad',**charges):
                    self.fail('invalid charge ran')

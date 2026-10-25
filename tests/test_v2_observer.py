from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
from unittest.mock import patch
import test_baseline_equivalence as tiny

from concept_firewall.v2_observer import GeneratorObserver, confidence_summary, run_pilot


@unittest.skipUnless(tiny.ML_AVAILABLE,"requires optional upstream Torch environment")
class GeneratorObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tiny.TinyUpstreamEquivalenceTests.setUpClass()
        cls.adapter=tiny.TinyUpstreamEquivalenceTests.adapter
        cls.context=tiny.TinyUpstreamEquivalenceTests.context
        cls.torch=tiny.TinyUpstreamEquivalenceTests.torch

    def observer(self):
        return GeneratorObserver(self.adapter,level=2,projection_dimension=8,seed=7)

    def test_full_generation_and_rng_invariance_with_boundary_callback(self):
        torch=self.torch
        control=self.adapter.generate(self.context)
        rng=torch.random.get_rng_state().clone()
        seen=[]
        codes,obs=self.observer().generate(self.context,seen.append)
        self.assertTrue(torch.equal(control,codes))
        self.assertTrue(torch.equal(rng,torch.random.get_rng_state()))
        self.assertEqual(seen,[obs])
        self.assertEqual(obs.level,2)
        self.assertEqual(len(obs.codes_prefix_by_sample[0]),2)
        self.assertEqual(len(obs.activation_by_sample[0]),8)
        self.assertEqual(len(obs.confidence_by_sample[0]),6)
        self.assertEqual(self.adapter.decode_final(control),self.adapter.decode_final(codes))
        with self.assertRaises(FrozenInstanceError):
            obs.level=3

    def test_future_mutation_cannot_change_observation(self):
        torch=self.torch
        before_codes,before=self.observer().generate(self.context)
        handle=self.adapter.generator.lm_heads[-1].register_forward_hook(lambda m,i,o:o.roll(1,dims=-1))
        try:
            after_codes,after=self.observer().generate(self.context)
        finally:
            handle.remove()
        self.assertEqual(before,after)
        self.assertFalse(torch.equal(before_codes,after_codes))

    def test_callback_precedes_future_head_and_artifacts_checked_before_loading(self):
        events=[]
        handle=self.adapter.generator.lm_heads[-1].register_forward_hook(lambda m,i,o:events.append('future'))
        try:
            self.observer().generate(self.context,lambda obs:events.append('observed'))
        finally:
            handle.remove()
        self.assertEqual(events,['observed','future'])
        with patch('concept_firewall.v2_protocol.require_contract',return_value=({}, {'artifact_sha256':{'expected':'hash'}})), \
             patch('concept_firewall.provenance.require_upstream'), \
             patch('concept_firewall.artifacts.verified_artifacts',return_value={}), \
             patch('concept_firewall.upstream_adapter.NCMAdapter.load') as load:
            with self.assertRaisesRegex(ValueError,'artifact hashes'):
                run_pilot(Path('.'),Path('unused'))
            load.assert_not_called()

    def test_cleanup_after_callback_failure_and_repeat_batch_order(self):
        model=self.adapter.generator
        count=len(model.lm_heads[1]._forward_hooks)
        def fail(obs):
            raise RuntimeError('callback failed')
        with self.assertRaisesRegex(RuntimeError,'callback failed'):
            self.observer().generate(self.context,fail)
        self.assertNotIn('_sample_level',model.__dict__)
        self.assertEqual(len(model.lm_heads[1]._forward_hooks),count)
        _,a=self.observer().generate(self.context)
        _,b=self.observer().generate(self.context)
        _,reversed_obs=self.observer().generate(self.context.flip(0))
        self.assertEqual(a,b)
        self.assertEqual(a.codes_prefix_by_sample,tuple(reversed(reversed_obs.codes_prefix_by_sample)))
        self.torch.testing.assert_close(self.torch.tensor(a.activation_by_sample),self.torch.tensor(list(reversed(reversed_obs.activation_by_sample))))

    def test_uniform_confidence_and_non_finite_guard(self):
        torch=self.torch
        log_prob=torch.log_softmax(torch.zeros(1,2,4),-1)
        values=confidence_summary(log_prob,torch.zeros(1,2,dtype=torch.long))
        self.assertAlmostEqual(float(values[0,0]),1)
        self.assertAlmostEqual(float(values[0,1]),1)
        self.assertEqual(float(values[0,2]),0)
        self.assertEqual(float(values[0,3]),0)
        log_prob[0,0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'Non-finite'):
            confidence_summary(log_prob,torch.zeros(1,2,dtype=torch.long))

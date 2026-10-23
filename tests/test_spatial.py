import unittest
import importlib.util

from concept_firewall.spatial import rademacher_projection, spatial_summaries, reconstruct_prefix
from concept_firewall.upstream_adapter import _activate_upstream
from pathlib import Path


@unittest.skipUnless(all(importlib.util.find_spec(name) is not None for name in ("torch","numpy","hydra","omegaconf")),"spatial tests need optional upstream research dependencies")
class SpatialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np,torch
        import numpy as np
        import torch

    def test_position_swaps_preserve_mean_but_change_spatial_features(self):
        latent=torch.arange(89*2,dtype=torch.float32).reshape(1,89,2)
        changed=latent.clone()
        changed[:,0,:],changed[:,80,:]=latent[:,80,:].clone(),latent[:,0,:].clone()
        row=torch.from_numpy(rademacher_projection(18,16,1))
        cell=torch.from_numpy(rademacher_projection(162,16,2))
        before=spatial_summaries(latent,row,cell)
        after=spatial_summaries(changed,row,cell)
        self.assertTrue(torch.equal(latent.mean(dim=1),changed.mean(dim=1)))
        self.assertFalse(torch.allclose(before[0],after[0]))
        self.assertFalse(torch.allclose(before[1],after[1]))

    def test_projection_is_frozen_without_fitted_labels(self):
        self.assertTrue(np.array_equal(rademacher_projection(12,16,7),rademacher_projection(12,16,7)))
        self.assertFalse(np.array_equal(rademacher_projection(12,16,7),rademacher_projection(12,16,8)))

    def test_separator_positions_are_excluded_from_spatial_features(self):
        latent=torch.zeros(1,89,2)
        changed=latent.clone()
        changed[:,[9,19,29,39,49,59,69,79],:]=100
        projections=(torch.from_numpy(rademacher_projection(18,16,1)),torch.from_numpy(rademacher_projection(162,16,2)))
        a,b=spatial_summaries(latent,*projections),spatial_summaries(changed,*projections)
        self.assertTrue(all(torch.equal(x,y) for x,y in zip(a,b)))

    def test_actual_upstream_prefix_rejects_future_codes(self):
        _activate_upstream((Path(__file__).resolve().parents[1]/"third_party/ncm").resolve())
        # Use the actual quantizer fixture already exercised by baseline tests.
        from test_baseline_equivalence import TinyUpstreamEquivalenceTests
        TinyUpstreamEquivalenceTests.setUpClass()
        adapter=TinyUpstreamEquivalenceTests.adapter
        codes=adapter.generate(TinyUpstreamEquivalenceTests.context)
        prefix=reconstruct_prefix(adapter.tokenizer.vqvae.vq,codes[:,:3],2)
        self.assertTrue(torch.equal(prefix,adapter.full_prefix_latents(codes)[1]))
        with self.assertRaises(ValueError):
            reconstruct_prefix(adapter.tokenizer.vqvae.vq,codes,2)

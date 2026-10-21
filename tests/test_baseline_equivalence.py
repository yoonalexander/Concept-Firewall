"""Equivalence checks on tiny random official components, not trained results.

These tests are explicitly skipped when the optional upstream ML environment
is missing. Passing them is source integration evidence, not reproduction of
the official hard-Sudoku checkpoint or solve rate.
"""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from concept_firewall.level_capture import collect_states
from concept_firewall.schema import puzzle_identity
from concept_firewall.upstream_adapter import GenerationSettings, NCMAdapter, _activate_upstream


ROOT = Path(__file__).resolve().parents[1]
ML_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("torch", "hydra", "omegaconf", "numpy"))


class LazyDependencyTests(unittest.TestCase):
    def test_importing_wrapper_does_not_import_ml_dependencies(self):
        code = "import sys; import concept_firewall.upstream_adapter; import concept_firewall.level_capture; assert not any(name in sys.modules for name in ('torch', 'omegaconf', 'hydra'))"
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        completed = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


@unittest.skipUnless(ML_AVAILABLE, "tiny upstream integration needs optional torch, numpy, Hydra, and OmegaConf")
class TinyUpstreamEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from omegaconf import OmegaConf
        cls.torch = torch
        cls.OmegaConf = OmegaConf
        _activate_upstream((ROOT / "third_party/ncm").resolve())
        from models.next_concept import NextConceptTransformer
        from models.vqvae import VQVAE
        from tokenization.sudoku_tokenizer import SudokuTokenizer

        config = OmegaConf.load(ROOT / "third_party/ncm/config/eval/sudoku-hard.yaml")
        config.model.n_layer, config.model.n_head, config.model.n_embd = 1, 2, 16
        config.model.prefix_len, config.model.context_length = 3, 7
        config.model.dropout = 0.0
        config.model.vocab_size = [4, 4, 4]
        vq_config = config.tokenizer.vqvae
        vq_config.context_length, vq_config.embed_dim, vq_config.n_layers = 4, 8, 2
        vq_config.vqvae_vocab_size = [4, 4, 4]
        vq_config.dropout = 0.0
        vq_config.vector_quantizer_config.levels.manual_levels = [1, 2, 4]
        torch.manual_seed(7)
        vqvae = VQVAE(**vq_config).eval()
        generator = NextConceptTransformer(vqvae_local=vqvae, config=config.model).eval()
        tokenizer = SimpleNamespace(vqvae=vqvae, pre_tokenizer=SudokuTokenizer())
        cls.config = config
        cls.adapter = NCMAdapter(tokenizer, generator, prefix_len=3)
        cls.context = torch.tensor([[11, 1, 2], [11, 3, 4]])

    def test_final_decode_matches_literal_official_path(self):
        adapter = self.adapter
        with self.torch.no_grad():
            codes = adapter.generator.generate(None, self.context, temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0, cfg_null_eos=None)
            _, levels = adapter.tokenizer.vqvae.vq.idx_to_zhats(codes, return_zlevels=True)
            ids = adapter.tokenizer.vqvae.decoder(levels[-1]).argmax(-1).tolist()
            # Upstream Sudoku EOS and PAD are both None, so only BOS is skipped.
            expected = tuple(adapter.tokenizer.pre_tokenizer.decode(row, skip_special_tokens=True) for row in ids)
        self.assertTrue(self.torch.equal(codes, adapter.generate(self.context)))
        self.assertEqual(adapter.decode_final(codes), expected)
        self.assertEqual(adapter.reconstruct_levels(codes)[-1].texts, expected)

    def test_actual_quantizer_prefix_is_independent_of_future_codes(self):
        codes = self.adapter.generate(self.context)
        changed = codes.clone()
        changed[:, 3:] = (changed[:, 3:] + 1) % 4
        before = self.adapter.reconstruct_levels(codes)
        after = self.adapter.reconstruct_levels(changed)
        for index in (0, 1):
            self.assertEqual(before[index].texts, after[index].texts)
            self.assertEqual(before[index].pooled_latents, after[index].pooled_latents)

    def test_prefix_snapshots_have_full_length_and_no_accumulator_aliasing(self):
        codes = self.adapter.generate(self.context)
        snapshots = self.adapter.full_prefix_latents(codes)
        self.assertTrue(all(state.shape[1] == self.adapter.levels[-1] for state in snapshots))
        _, official = self.adapter.tokenizer.vqvae.vq.idx_to_zhats(codes, return_zlevels=True)
        self.assertTrue(self.torch.equal(snapshots[-1], official[-1]))
        first = snapshots[0].clone()
        snapshots[-1].add_(999)
        self.assertTrue(self.torch.equal(snapshots[0], first))

    def test_capture_does_not_change_future_baseline_generations(self):
        before = self.adapter.generate(self.context)
        seen = []
        collect_states(self.adapter, before, run_id="tiny-test", puzzle_ids=[puzzle_identity("0" * 81)] * 2, trajectory_ids=["a", "b"], observer=seen.append)
        after = self.adapter.generate(self.context)
        self.assertEqual(len(seen), 6)
        self.assertTrue(self.torch.equal(before, after))
        self.assertEqual(self.adapter.decode_final(before), self.adapter.decode_final(after))

    def test_load_reads_two_tiny_checkpoints_with_strict_state_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.torch.save({"model": self.adapter.tokenizer.vqvae.state_dict()}, path / "tokenizer.pt")
            self.torch.save({"model": self.adapter.generator.state_dict()}, path / "generator.pt")
            self.OmegaConf.save(self.config, path / "config.yaml")
            loaded = NCMAdapter.load(ROOT / "third_party/ncm", path / "config.yaml", path, device="cpu")
            self.assertEqual(set(loaded.checkpoint_paths), {"tokenizer", "generator"})
            self.assertTrue(self.torch.equal(loaded.generate(self.context), self.adapter.generate(self.context)))
            self.assertEqual(loaded.decode_final(loaded.generate(self.context)), self.adapter.decode_final(self.adapter.generate(self.context)))
            self.torch.save({"model": {}}, path / "generator.pt")
            with self.assertRaises(RuntimeError):
                NCMAdapter.load(ROOT / "third_party/ncm", path / "config.yaml", path, device="cpu")


if __name__ == "__main__":
    unittest.main()

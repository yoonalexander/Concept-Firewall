"""Unit tests with explicit tensor fixtures, not checkpoint reproduction."""

from dataclasses import FrozenInstanceError
import importlib.util
import unittest
from types import SimpleNamespace

from concept_firewall.level_capture import collect_states, states_from_reconstructions
from concept_firewall.schema import puzzle_identity
from concept_firewall.timing import timed_call
from concept_firewall.upstream_adapter import GenerationSettings, NCMAdapter, UnsupportedConfigurationError


TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


def fixture_adapter():
    """Use fake components and real tensors so wrapper behavior is isolated."""
    import torch

    class FakeQuantizer:
        levels = (1, 2, 4)
        embed_dim = 2

        def __init__(self):
            self.embeddings = [lambda ids: torch.stack((ids.float(), ids.float()+1), dim=-1) for _ in self.levels]

        def get_next_autoregressive_input(self, index, cumulative, embedding):
            cumulative[:, :, 0] += embedding[:, :, 0].sum(dim=1)[:, None]
            cumulative[:, :, 1] = cumulative[:, :, 0] + 1
            return cumulative, cumulative

        def idx_to_zhats(self, codes, return_zlevels=True):
            assert return_zlevels
            latents = []
            offset = 0
            for length in self.levels:
                offset += length
                value = codes[:, :offset].float().sum(dim=1)
                latent = torch.stack((value, value + 1), dim=-1)[:, None, :].expand(-1, length, -1).clone()
                latents.append(latent)
            return [], latents

    class FakeDecoder:
        def __call__(self, latent):
            ids = latent[:, :, 0].long() % 10
            return torch.nn.functional.one_hot(ids, num_classes=12).float()

    class FakePreTokenizer:
        eos_token_id = None
        pad_token_id = None

        def decode(self, ids, skip_special_tokens=False):
            assert skip_special_tokens
            return "".join("_123456789|B"[value] for value in ids if value != 11)

    class FakeGenerator:
        calls = 0

        def generate(self, level0, context, **kwargs):
            assert level0 is None
            assert kwargs == dict(temperature=0.0, top_k=0, top_p=1.0, cfg_scale=0.0, cfg_null_eos=None)
            self.calls += 1
            return torch.tensor([[1, 2, 3, 4, 5, 6, 7]] * context.shape[0], dtype=torch.long)

    tokenizer = SimpleNamespace(vqvae=SimpleNamespace(vq=FakeQuantizer(), decoder=FakeDecoder()), pre_tokenizer=FakePreTokenizer())
    return NCMAdapter(tokenizer, FakeGenerator(), prefix_len=3)


class SettingsAndTimingTests(unittest.TestCase):
    def test_unsupported_penalties_are_explicit(self):
        for name, value in (("frequency_penalty", .1), ("frequency_deficit", .2), ("adjacency_penalty", "1,2"), ("level0_unigram", "prior.pt")):
            with self.subTest(name=name), self.assertRaises(UnsupportedConfigurationError):
                GenerationSettings.from_config({name: value})

    def test_generation_settings_reject_invalid_values(self):
        for kwargs in ({"temperature": float("nan")}, {"temperature": -1}, {"top_k": -1}, {"top_p": 2}, {"cut_at_eos": "false"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                GenerationSettings(**kwargs)

    def test_cpu_timing_needs_no_torch_call(self):
        result = timed_call(lambda: "answer", device="cpu")
        self.assertEqual(result.value, "answer")
        self.assertGreaterEqual(result.elapsed_ms, 0)


@unittest.skipUnless(TORCH_AVAILABLE, "tensor-fixture unit tests require optional PyTorch")
class PartialReconstructionTests(unittest.TestCase):
    def setUp(self):
        import torch
        self.torch = torch
        self.adapter = fixture_adapter()
        self.codes = torch.tensor([[1, 2, 3, 4, 5, 6, 7], [0, 1, 2, 3, 4, 5, 6]])

    def test_all_levels_final_equivalence_and_mean_pooling(self):
        levels = self.adapter.reconstruct_levels(self.codes)
        self.assertEqual(len(levels), 3)
        self.assertEqual(levels[-1].texts, self.adapter.decode_final(self.codes))
        self.assertEqual(levels[0].pooled_latents, ((1.0, 2.0), (0.0, 1.0)))
        self.assertEqual(levels[1].pooled_latents, ((6.0, 7.0), (3.0, 4.0)))
        self.assertEqual(levels[1].codes_prefix_by_sample[0], ((1,), (2, 3)))
        self.assertTrue(all(level.decode_ms >= 0 for level in levels))

    def test_future_codes_do_not_change_earlier_export(self):
        changed = self.codes.clone()
        changed[:, 3:] = 15
        before = self.adapter.reconstruct_levels(self.codes)
        after = self.adapter.reconstruct_levels(changed)
        for index in (0, 1):
            self.assertEqual(before[index].codes_prefix_by_sample, after[index].codes_prefix_by_sample)
            self.assertEqual(before[index].texts, after[index].texts)
            self.assertEqual(before[index].pooled_latents, after[index].pooled_latents)
        self.assertNotEqual(before[-1].pooled_latents, after[-1].pooled_latents)

    def test_capture_is_sample_major_and_has_no_final_label(self):
        puzzles = ("0" * 81, "1" + "0" * 80)
        states = collect_states(self.adapter, self.codes, run_id="run", puzzle_ids=[puzzle_identity(p) for p in puzzles], trajectory_ids=["a", "b"])
        self.assertEqual([[state.level for state in row] for row in states], [[1, 2, 3], [1, 2, 3]])
        self.assertEqual(states[1][1].codes_prefix, ((0,), (1, 2)))
        self.assertFalse(hasattr(states[0][0], "final_valid"))
        self.assertFalse(hasattr(states[0][0], "generator_ms_incremental"))

    def test_observer_cannot_mutate_model_codes_or_states(self):
        snapshot = self.codes.clone()
        seen = []

        def observer(state):
            with self.assertRaises(FrozenInstanceError):
                state.predicted_board = "changed"
            with self.assertRaises(TypeError):
                state.codes_prefix[0][0] = 99
            seen.append(state)

        states = collect_states(self.adapter, self.codes, run_id="run", puzzle_ids=[puzzle_identity("0" * 81)] * 2, trajectory_ids=["a", "b"], observer=observer)
        self.assertEqual(len(seen), 6)
        self.assertTrue(self.torch.equal(snapshot, self.codes))
        self.assertEqual(tuple(row[-1].predicted_board for row in states), self.adapter.decode_final(self.codes))

    def test_observer_errors_propagate(self):
        def observer(_state):
            raise RuntimeError("observer failed")
        with self.assertRaisesRegex(RuntimeError, "observer failed"):
            collect_states(self.adapter, self.codes, run_id="run", puzzle_ids=[puzzle_identity("0" * 81)] * 2, trajectory_ids=["a", "b"], observer=observer)

    def test_metadata_and_code_shape_mismatches_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.reconstruct_levels(self.codes[:, :-1])
        levels = self.adapter.reconstruct_levels(self.codes)
        with self.assertRaises(ValueError):
            states_from_reconstructions(levels, run_id="run", puzzle_ids=[puzzle_identity("0" * 81)], trajectory_ids=["a"])
        with self.assertRaises(ValueError):
            states_from_reconstructions(levels[1:], run_id="run", puzzle_ids=[puzzle_identity("0" * 81)] * 2, trajectory_ids=["a", "b"])

    def test_undefined_sudoku_padding_and_text_inputs_rejected(self):
        for items in ([[1, 2]], ["123"]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                self.adapter.prepare_context(items)
        context = self.adapter.prepare_context([[1, 2, 3, 4]])
        self.assertEqual(context.tolist(), [[1, 2, 3]])

    def test_eos_pad_and_special_token_behavior_matches_evaluator(self):
        pre = self.adapter.tokenizer.pre_tokenizer
        pre.eos_token_id, pre.pad_token_id = 9, 0
        self.assertEqual(self.adapter._decode_ids([1, 0, 2, 9, 3]), "12")
        self.adapter.generation_settings = GenerationSettings(cut_at_eos=False)
        self.assertEqual(self.adapter._decode_ids([1, 0, 2, 9, 3]), "123")


if __name__ == "__main__":
    unittest.main()

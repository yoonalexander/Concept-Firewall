"""The feature API cannot read future codes, reconstructions, or final labels."""

from dataclasses import fields, replace
import inspect
import math
import unittest

from concept_firewall.representations import extract_features, make_level_record
from concept_firewall.schema import LevelState, TrajectoryOutcome, puzzle_identity


PUZZLE = "0" * 81


class PrefixFeatureTests(unittest.TestCase):
    def test_future_mutations_cannot_affect_level_k_features(self):
        full_codes = [[1], [2, 3], [4, 5, 6], [7, 8, 9, 10]]
        boards = ["0" * 81, "1" + "0" * 80, "future text", "final text"]
        latents = [[1.0], [2.0, 4.0], [999.0], [-999.0]]
        current = LevelState(
            run_id="r", puzzle_id=puzzle_identity(PUZZLE), trajectory_id="t", level=2,
            codes_prefix=full_codes[:2], predicted_board=boards[1], pooled_latent=latents[1],
        )
        before = extract_features(current, PUZZLE)
        full_codes[2:] = [[99], [100]]
        boards[2:] = ["different future", "different final"]
        latents[2:] = [[1e100], [-1e100]]
        self.assertEqual(extract_features(current, PUZZLE), before)
        # Defensive copies also prevent aliasing mutable collector buffers.
        full_codes[0][0] = 99
        latents[1][0] = 99.0
        self.assertEqual(extract_features(current, PUZZLE), before)

    def test_outcomes_have_no_entry_point_into_feature_extraction(self):
        state = LevelState("r", puzzle_identity(PUZZLE), "t", 1, ((2,),), PUZZLE)
        outcome = TrajectoryOutcome(
            "r", puzzle_identity(PUZZLE), "t", False, "config", 0,
            {"generator": "a" * 64}, "b" * 40, "malformed final board",
        )
        features = extract_features(state, PUZZLE)
        changed = replace(outcome, final_valid=True, final_board="9" * 81)
        self.assertNotEqual(changed, outcome)
        self.assertEqual(extract_features(state, PUZZLE), features)
        self.assertEqual(list(inspect.signature(extract_features).parameters), ["state", "puzzle"])
        self.assertNotIn("final_valid", {field.name for field in fields(LevelState)})
        for forbidden in (outcome, make_level_record(state, PUZZLE), {"state": state, "outcome": outcome}):
            with self.subTest(kind=type(forbidden)), self.assertRaises(TypeError):
                extract_features(forbidden, PUZZLE)
        with self.assertRaises(TypeError):
            extract_features(state, PUZZLE, outcome)
        self.assertFalse(any("final" in name or "outcome" in name for name in features))

    def test_future_prefix_is_rejected_at_current_level(self):
        with self.assertRaisesRegex(ValueError, "exactly level"):
            LevelState("r", puzzle_identity(PUZZLE), "t", 1, ((2,), (3, 4)), PUZZLE)

    def test_wrong_puzzle_cannot_silently_change_features(self):
        state = LevelState("r", puzzle_identity(PUZZLE), "t", 1, ((2,),), PUZZLE)
        with self.assertRaisesRegex(ValueError, "puzzle content"):
            extract_features(state, "1" + "0" * 80)

    def test_features_are_finite_reference_free_and_immutable(self):
        state = LevelState("r", puzzle_identity(PUZZLE), "t", 2, ((1,), (1, 2)), PUZZLE, (2, 4))
        features = extract_features(state, PUZZLE)
        self.assertEqual(features["codes.count"], 3.0)
        self.assertEqual(features["codes.unique_fraction"], 2 / 3)
        self.assertEqual(features["latent.mean"], 3.0)
        self.assertEqual(features["latent.std"], 1.0)
        self.assertEqual(features["latent.l2"], math.sqrt(20))
        self.assertEqual(features["decoded.current_valid"], 0.0)
        self.assertTrue(all(math.isfinite(value) for value in features.values()))
        with self.assertRaises(TypeError):
            features["new"] = 1.0

    def test_code_id_permutation_preserves_categorical_summary(self):
        state = LevelState("r", puzzle_identity(PUZZLE), "t", 2, ((1,), (1, 2)), PUZZLE)
        permuted = replace(state, codes_prefix=((500,), (500, 42)))
        self.assertEqual(extract_features(state, PUZZLE), extract_features(permuted, PUZZLE))


if __name__ == "__main__":
    unittest.main()

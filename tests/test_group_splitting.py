import unittest
from concept_firewall.training import split_puzzles


class GroupSplitTests(unittest.TestCase):
    def test_duplicate_puzzles_never_cross_four_partitions(self):
        fractions = {"train": .5, "validation": .15, "calibration": .15, "test": .2}
        ids = [str(i) for i in range(100)] * 4
        split = split_puzzles(ids, seed=42, fractions=fractions)
        flattened = [key for group in split.values() for key in group]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(set(flattened), set(ids))
        self.assertEqual(split, split_puzzles(list(reversed(ids)), seed=42, fractions=fractions))
        self.assertEqual([len(group) for group in split.values()], [50, 15, 15, 20])

    def test_invalid_and_tiny_partitions_rejected(self):
        with self.assertRaises(ValueError):
            split_puzzles(["a"], seed=0, fractions={"train": 1})
        with self.assertRaises(ValueError):
            split_puzzles(["a", "b"], seed=0, fractions={"train": .5, "validation": .15, "calibration": .15, "test": .2})

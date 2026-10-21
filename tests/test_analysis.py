"""Synthetic fixtures verify validation/transition arithmetic, not model quality."""
import json
from pathlib import Path
import tempfile
import unittest

from concept_firewall.analysis import load_complete_trajectories, summarize_trajectories
from concept_firewall.schema import LevelRecord, TrajectoryOutcome, puzzle_identity
from concept_firewall.storage import write_level_records, write_outcomes


class AnalysisTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / "trajectories"
        directory.mkdir()
        puzzle_id = puzzle_identity("0" * 81)
        rows, labels = [], []
        for name, states in (("repair", (False, True)), ("damage", (True, False))):
            for level, correct in enumerate(states, 1):
                rows.append(LevelRecord("run", puzzle_id, name, level, tuple((1,) for _ in range(level)), "1" * 81, correct, {"decoded.malformed": 0}))
            labels.append(TrajectoryOutcome("run", puzzle_id, name, states[-1], "config", 0, {"generator": "a" * 64}, "b" * 40, "1" * 81))
        write_level_records(directory / "levels.jsonl", rows)
        write_outcomes(directory / "outcomes.jsonl", labels)
        manifest = {"mode": "collection", "status": "passed", "run_id": "run", "trajectory_directory": "trajectories", "records": 4, "trajectories": 2, "total_levels": 2, "unique_puzzles": 1, "solved": 1}
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest))
        return path, manifest

    def test_repairs_and_late_failures_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, _ = self.fixture(root)
            _, grouped, _ = load_complete_trajectories(root, path)
            result = summarize_trajectories(grouped)
            self.assertEqual(result["categories"], {"repaired_by_final_level": 1, "became_wrong_by_final_level": 1})
            self.assertEqual(result["transitions"][0]["wrong_right"], 1)
            self.assertEqual(result["transitions"][0]["right_wrong"], 1)
            self.assertEqual(result["per_level"][0]["unique_puzzles"], 1)

    def test_uniform_truncation_fails_expected_level_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest = self.fixture(root)
            manifest["total_levels"] = 3
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "all expected levels"):
                load_complete_trajectories(root, path)

    def test_manifest_cannot_claim_unobserved_successes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path, manifest = self.fixture(root)
            manifest["solved"] = 2
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "summary differs"):
                load_complete_trajectories(root, path)


if __name__ == "__main__":
    unittest.main()

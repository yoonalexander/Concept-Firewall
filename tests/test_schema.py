"""Validation, immutability and storage contracts for research observations."""

from dataclasses import FrozenInstanceError, replace
import builtins
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from concept_firewall.representations import make_level_record
from concept_firewall.schema import LevelRecord, LevelState, TrajectoryOutcome, puzzle_identity
from concept_firewall.storage import (
    export_parquet, read_level_records, read_outcomes, record_from_dict,
    record_to_dict, write_level_records, write_outcomes,
)


PUZZLE = "0" * 81
SOLUTION = (
    "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
)


def state(**changes):
    values = dict(
        run_id="test-run", puzzle_id=puzzle_identity(PUZZLE), trajectory_id="trajectory-0",
        level=2, codes_prefix=((4,), (2, 3)), predicted_board=SOLUTION,
        pooled_latent=(1.0, 2.0, 3.0),
    )
    values.update(changes)
    return LevelState(**values)


def outcome(**changes):
    values = dict(
        run_id="test-run", puzzle_id=puzzle_identity(PUZZLE), trajectory_id="trajectory-0",
        final_valid=True, configuration_id="sudoku-hard-config-sha256", seed=7,
        checkpoint_sha256={"generator.pt": "a" * 64, "tokenizer.pt": "b" * 64},
        upstream_commit="c" * 40, final_board=SOLUTION,
    )
    values.update(changes)
    return TrajectoryOutcome(**values)


class SchemaTests(unittest.TestCase):
    def test_puzzle_identity_is_content_based_and_canonical(self):
        self.assertEqual(puzzle_identity(PUZZLE), puzzle_identity("\n ".join("." * 81)))
        self.assertNotEqual(puzzle_identity(PUZZLE), puzzle_identity("1" + "0" * 80))
        with self.assertRaises(ValueError):
            puzzle_identity("row-42")

    def test_state_copies_mutable_inputs_and_is_frozen(self):
        codes = [[4], [2, 3]]
        latent = [1.0, 2.0]
        observed = state(codes_prefix=codes, pooled_latent=latent)
        codes[0][0] = 99
        latent[0] = 99
        self.assertEqual(observed.codes_prefix, ((4,), (2, 3)))
        self.assertEqual(observed.pooled_latent, (1.0, 2.0))
        with self.assertRaises(FrozenInstanceError):
            observed.level = 3

    def test_invalid_states_fail_at_boundary(self):
        for changes in (
            {"run_id": ""}, {"trajectory_id": " x"}, {"puzzle_id": "row-42"},
            {"level": 0}, {"level": True}, {"level": 1.0},
            {"codes_prefix": ((1,),)}, {"codes_prefix": ((1,), ())},
            {"codes_prefix": ((1,), (-1,))}, {"codes_prefix": ((True,), (2,))},
            {"pooled_latent": (float("nan"),)}, {"pooled_latent": (float("inf"),)},
            {"pooled_latent": (True,)}, {"predicted_board": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                state(**changes)

    def test_malformed_output_is_representable_as_failure(self):
        record = make_level_record(state(predicted_board="unparseable"), PUZZLE)
        self.assertFalse(record.current_valid)
        self.assertEqual(record.features["decoded.malformed"], 1.0)

    def test_record_and_outcome_mappings_are_immutable_copies(self):
        features = {"example": 1.0}
        record = replace(make_level_record(state(), PUZZLE), features=features)
        features["example"] = 2.0
        self.assertEqual(record.features["example"], 1.0)
        with self.assertRaises(TypeError):
            record.features["example"] = 3.0
        hashes = {"generator.pt": "a" * 64}
        label = outcome(checkpoint_sha256=hashes)
        hashes["generator.pt"] = "d" * 64
        self.assertEqual(label.checkpoint_sha256["generator.pt"], "a" * 64)
        with self.assertRaises(TypeError):
            label.checkpoint_sha256["generator.pt"] = "b" * 64

    def test_timing_is_nullable_and_never_fabricated(self):
        record = make_level_record(state(), PUZZLE)
        self.assertIsNone(record.generator_ms_incremental)
        self.assertIsNone(record.monitor_ms_incremental)
        self.assertIsNone(record.decode_ms_incremental)
        for name in ("generator_ms_incremental", "monitor_ms_incremental", "decode_ms_incremental"):
            for value in (-1, float("inf"), float("nan"), True):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    replace(record, **{name: value})

    def test_outcome_rejects_missing_or_ambiguous_provenance(self):
        for changes in (
            {"seed": True}, {"seed": -1}, {"final_valid": 1},
            {"checkpoint_sha256": {}}, {"checkpoint_sha256": {"generator": "unknown"}},
            {"checkpoint_sha256": {"": "a" * 64}}, {"upstream_commit": "abc123"},
            {"configuration_id": ""}, {"final_board": None},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                outcome(**changes)

    def test_feature_values_and_versions_are_validated(self):
        record = make_level_record(state(), PUZZLE)
        for changes in (
            {"features": {"x": math.nan}}, {"features": {"x": math.inf}},
            {"features": {"x": True}}, {"features": {"": 1.0}},
            {"available_feature_version": "future-v2"}, {"current_valid": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(record, **changes)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "records.jsonl"
        self.record = make_level_record(state(), PUZZLE)

    def write_payload(self, payload):
        self.path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def test_level_and_outcome_roundtrip_are_separate(self):
        write_level_records(self.path, [self.record])
        self.assertEqual(read_level_records(self.path), (self.record,))
        outcome_path = self.path.with_name("outcomes.jsonl")
        label = outcome()
        write_outcomes(outcome_path, [label])
        self.assertEqual(read_outcomes(outcome_path), (label,))
        with self.assertRaisesRegex(ValueError, "separately"):
            read_level_records(outcome_path)
        with self.assertRaisesRegex(ValueError, "separately"):
            read_outcomes(self.path)
        with self.assertRaises(TypeError):
            write_level_records(self.path.with_name("mixed.jsonl"), [self.record, label])

    def test_existing_results_protected_and_explicit_overwrite_works(self):
        write_level_records(self.path, [self.record])
        with self.assertRaises(FileExistsError):
            write_level_records(self.path, [self.record])
        replacement = replace(self.record, predicted_board="malformed", current_valid=False)
        write_level_records(self.path, [replacement], overwrite=True)
        self.assertEqual(read_level_records(self.path), (replacement,))

    def test_unknown_versions_extra_fields_and_incomplete_records_rejected(self):
        for version in (2, "1", True, None):
            payload = record_to_dict(self.record)
            payload["schema_version"] = version
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "schema_version"):
                record_from_dict(payload)
        for field, action in (("future_label", "add"), ("run_id", "remove")):
            payload = record_to_dict(self.record)
            if action == "add":
                payload[field] = True
            else:
                del payload[field]
            self.write_payload(payload)
            with self.assertRaisesRegex(ValueError, "line 1.*record fields"):
                read_level_records(self.path)

    def test_nonfinite_numbers_and_duplicate_keys_rejected(self):
        payload = record_to_dict(self.record)
        for value in (math.nan, math.inf, -math.inf):
            payload["features"] = {"bad": value}
            self.write_payload(payload)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "non-finite"):
                read_level_records(self.path)
        payload["features"] = {"bad": 1.0}
        self.path.write_text(json.dumps(payload).replace('"bad": 1.0', '"bad": 1e400'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "finite"):
            read_level_records(self.path)
        self.path.write_text('{"schema_version": 1, "schema_version": 1}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            read_level_records(self.path)

    def test_duplicate_record_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate record"):
            write_level_records(self.path, [self.record, self.record])
        payload = json.dumps(record_to_dict(self.record)) + "\n"
        self.path.write_text(payload * 2, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "line 2.*duplicate record"):
            read_level_records(self.path)

    def test_invalid_overwrite_does_not_truncate_existing_result(self):
        write_level_records(self.path, [self.record])
        original = self.path.read_bytes()
        with self.assertRaises(TypeError):
            write_level_records(self.path, [outcome()], overwrite=True)
        self.assertEqual(self.path.read_bytes(), original)

    def test_parquet_missing_extra_has_actionable_error(self):
        real_import = builtins.__import__

        def no_arrow(name, *args, **kwargs):
            if name.startswith("pyarrow"):
                raise ImportError("test: pyarrow unavailable")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=no_arrow):
            with self.assertRaisesRegex(RuntimeError, r"concept-firewall\[parquet\]"):
                export_parquet(self.path.with_suffix(".parquet"), [self.record])

    def test_parquet_export_when_extra_is_installed(self):
        try:
            import pyarrow.parquet as pq
        except ImportError:
            self.skipTest("pyarrow extra not installed")
        destination = self.path.with_suffix(".parquet")
        export_parquet(destination, [self.record])
        restored = pq.read_table(destination).to_pylist()
        self.assertEqual(restored[0]["schema_version"], 1)
        self.assertEqual(restored[0]["codes_prefix"], [[4], [2, 3]])
        self.assertIsNone(restored[0]["generator_ms_incremental"])
        self.assertNotIn("final_valid", restored[0])
        final_path = destination.with_name("outcomes.parquet")
        export_parquet(final_path, [outcome()])
        self.assertTrue(pq.read_table(final_path).to_pylist()[0]["final_valid"])


if __name__ == "__main__":
    unittest.main()

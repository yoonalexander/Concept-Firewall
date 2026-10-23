"""Audit portable predictions and train-only scaler statistics after fitting."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pickle

import numpy as np

from concept_firewall.artifacts import sha256_file, verified_artifacts
from concept_firewall.probes import LinearProbe, feature_vector
from concept_firewall.schema import LevelState, puzzle_identity

parser = argparse.ArgumentParser()
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--output", type=Path, help="Write a new audit without overwriting historical evidence")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manifest_path = args.manifest.resolve()
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("mode") != "probes" or manifest.get("status") != "passed":
    raise ValueError("A completed probe manifest is required")
verified_artifacts(root)
collection_path = root / manifest["configuration"]["collection_manifest"]
collection = json.loads(collection_path.read_text(encoding="utf-8"))
with (root / "data/sudoku-hard/puzzles.pickle").open("rb") as stream:
    contexts = pickle.load(stream)  # Reviewed digest checked above.
puzzles = {}
for context in contexts:
    if len(context) != 91 or context[0] != 11 or context[-1] != 11:
        raise ValueError("Unexpected official context framing")
    puzzle = "".join("_123456789|"[token] for token in context[1:-1])
    puzzles[puzzle_identity(puzzle)] = puzzle
level = manifest["configuration"]["protocol"]["primary_level"]
rows = {}
with (root / collection["trajectory_directory"] / "levels.jsonl").open(encoding="utf-8") as stream:
    for line in stream:
        row = json.loads(line)
        if row["level"] == level:
            rows[row["puzzle_id"]] = row
destination = root / manifest["probe_directory"]
prediction_path = destination / f"level-{level:02d}-test_predictions.json"
expected = json.loads(prediction_path.read_text(encoding="utf-8"))
split_path = root / manifest["split_manifest"]
if sha256_file(split_path) != manifest["split_sha256"]:
    raise ValueError("Frozen splits changed after training")
splits = json.loads(split_path.read_text(encoding="utf-8"))
checks = {}
for family in ("input", "decoded", "latent", "input_decoded", "input_decoded_latent"):
    path = destination / f"level-{level:02d}-{family}.json"
    probe = LinearProbe.load(path)
    training_vectors = [feature_vector(rows[key]["features"], tuple(tuple(c) for c in rows[key]["codes_prefix"]), family)[1] for key in splits["train"]]
    actual_mean = np.asarray(training_vectors).mean(axis=0)
    if not np.allclose(probe.mean, actual_mean, rtol=1e-12, atol=1e-12):
        raise ValueError(f"Saved {family} scaler does not match training-only statistics")
    largest_error = 0.0
    for index, key in enumerate(expected["puzzle_ids"]):
        row = rows[key]
        state = LevelState(row["run_id"], row["puzzle_id"], row["trajectory_id"], row["level"], row["codes_prefix"], row["predicted_board"], row["pooled_latent"])
        probability = probe.predict_failure_probability(state, puzzles[key])
        largest_error = max(largest_error, abs(probability-expected["probabilities"][family][index]))
    if largest_error > 1e-12:
        raise ValueError(f"Portable {family} predictions differ from held-out evaluation: {largest_error}")
    checks[family] = {"probe_sha256": sha256_file(path), "test_predictions_checked": len(expected["puzzle_ids"]), "max_absolute_probability_error": largest_error, "scaler_train_only_mean_verified": True}
report = root / "results/manifests" / f"{manifest['run_id']}-artifact_validation.json"
if args.output is not None:
    report = args.output.resolve()
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps({"status": "passed", "probe_manifest_sha256": sha256_file(manifest_path), "collection_manifest_sha256": sha256_file(collection_path), "script_sha256": sha256_file(Path(__file__)), "level": level, "checks": checks}, indent=2) + "\n", encoding="utf-8")
print(report)

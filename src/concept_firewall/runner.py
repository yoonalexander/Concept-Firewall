"""Baseline and full-depth observational runs, kept separate from future policy runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import time

from .artifacts import verified_artifacts
from .provenance import new_manifest, require_upstream, save_manifest


def read_configuration(root: Path, path: Path) -> dict:
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("Install the research extra to read experiment YAML") from error
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"upstream_root", "upstream_config", "checkpoint_dir", "data_dir", "n", "batch_size", "seed", "device"}
    if not isinstance(config, dict) or not required <= config.keys():
        raise ValueError(f"Experiment config requires {sorted(required)}")
    for key in ("n", "batch_size"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if type(config["seed"]) is not int or config["seed"] < 0 or config["device"] != "cuda":
        raise ValueError("This upstream-equivalent runner requires CUDA and an integer seed")
    # This release is pinned to reviewed official artifacts, not arbitrary pickle sources.
    for key, expected in (("upstream_root", "third_party/ncm"), ("upstream_config", "third_party/ncm/config/eval/sudoku-hard.yaml"), ("checkpoint_dir", "artifacts/sudoku-hard"), ("data_dir", "data/sudoku-hard")):
        if config[key] != expected:
            raise ValueError(f"{key} must be {expected!r} for the verified hard-Sudoku release")
    return config


def preflight(root: Path, config: dict) -> dict[str, str]:
    require_upstream(root)
    hashes = verified_artifacts(root)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in this Python environment; run doctor and install CUDA PyTorch in .venv")
    return hashes


def baseline(root: Path, config: dict) -> Path:
    manifest = new_manifest(root, "baseline", config)
    save_manifest(root, manifest)
    try:
        hashes = preflight(root, config)
        raw = root / "results/raw" / manifest["run_id"]
        raw.mkdir(parents=True)
        command = [sys.executable, "evaluate.py", "--config", str(root / config["upstream_config"]), "--checkpoint-dir", str(root / config["checkpoint_dir"]), "--data-dir", str(root / config["data_dir"]), "--gpus", "0", "--n", str(config["n"]), "--bs", str(config["batch_size"]), "--out", str(raw)]
        manifest.update(artifact_sha256=hashes, upstream_command=command, raw_directory=str(raw.relative_to(root)))
        save_manifest(root, manifest)
        started = time.perf_counter()
        with (raw / "evaluate.log").open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=root / config["upstream_root"], stdout=stream, stderr=subprocess.STDOUT)
        manifest["process_wall_ms"] = (time.perf_counter() - started) * 1000
        if result.returncode:
            raise RuntimeError(f"Official evaluator failed ({result.returncode}); see {raw}")
        with (raw / "shard_0.pkl").open("rb") as stream:
            part = pickle.load(stream)  # Only output of the reviewed upstream process.
        if len(part["hyps"]) != config["n"]:
            raise ValueError("Official evaluator returned an unexpected sample count")
        manifest.update(status="passed", samples=len(part["hyps"]), upstream_metrics_log=(raw / "evaluate.log").read_text(encoding="utf-8"))
    except Exception as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_manifest(root, manifest)
        raise
    return save_manifest(root, manifest)


def collect(root: Path, config: dict, baseline_path: Path) -> Path:
    from .schema import TrajectoryOutcome, puzzle_identity
    from .storage import write_level_records, write_outcomes, export_parquet
    from .representations import make_level_record
    from .upstream_adapter import NCMAdapter
    from .level_capture import collect_states
    from .sudoku_labels import verify_sudoku

    reference = json.loads(baseline_path.read_text(encoding="utf-8"))
    if reference.get("mode") != "baseline" or reference.get("status") != "passed" or reference.get("configuration") != config:
        raise ValueError("Collection requires a successful official baseline with identical configuration")
    manifest = new_manifest(root, "collection", config)
    manifest["baseline_manifest"] = str(baseline_path.relative_to(root))
    save_manifest(root, manifest)
    try:
        hashes = preflight(root, config)
        if hashes != reference["artifact_sha256"] or reference["upstream_commit"] != manifest["upstream_commit"]:
            raise ValueError("Baseline provenance differs from collection")
        import torch
        torch.manual_seed(config["seed"])
        with (root / config["data_dir"] / "puzzles.pickle").open("rb") as stream:
            items = pickle.load(stream)[:config["n"]]  # Digest-verified pinned public benchmark only.
        if len(items) != config["n"]:
            raise ValueError("Requested more puzzles than the dataset contains")
        with (root / reference["raw_directory"] / "shard_0.pkl").open("rb") as stream:
            official = pickle.load(stream)
        expected = dict(zip(official["idxs"], official["hyps"]))
        adapter = NCMAdapter.load(root / config["upstream_root"], root / config["upstream_config"], root / config["checkpoint_dir"], device=config["device"])
        manifest["reconstruction_contract"] = "full-cumulative-prefix-v2"
        all_records, outcomes, costs = [], [], []
        config_id = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        # Warmup is outside recorded batch timing and explicitly recorded below.
        adapter.generate(adapter.prepare_context(items[:1]))
        torch.manual_seed(config["seed"])
        for offset in range(0, len(items), config["batch_size"]):
            batch = items[offset:offset + config["batch_size"]]
            puzzles = [adapter.tokenizer.pre_tokenizer.decode(list(item), skip_special_tokens=True) for item in batch]
            puzzle_ids = [puzzle_identity(puzzle) for puzzle in puzzles]
            trajectory_ids = [f"{manifest['run_id']}:{offset + i}" for i in range(len(batch))]
            codes, generation_ms = adapter.generate_timed(adapter.prepare_context(batch))
            final = adapter.decode_final(codes)
            if tuple(expected[offset + i] for i in range(len(batch))) != tuple(final):
                raise ValueError(f"Uninstrumented wrapper differs from official predictions at batch {offset}")
            started = time.perf_counter()
            states = collect_states(adapter, codes, run_id=manifest["run_id"], puzzle_ids=puzzle_ids, trajectory_ids=trajectory_ids)
            for i, trajectory in enumerate(states):
                if trajectory[-1].predicted_board != final[i]:
                    raise ValueError("Instrumented final reconstruction differs from baseline")
                for state in trajectory:
                    all_records.append(make_level_record(state, puzzles[i]))
                outcomes.append(TrajectoryOutcome(run_id=manifest["run_id"], puzzle_id=puzzle_ids[i], trajectory_id=trajectory_ids[i], final_valid=verify_sudoku(puzzles[i], final[i]), configuration_id=config_id, seed=config["seed"], checkpoint_sha256={k:v for k,v in hashes.items() if k.startswith("artifacts/")}, upstream_commit=manifest["upstream_commit"], final_board=final[i]))
            costs.append({"offset": offset, "batch_size": len(batch), "generator_total_ms": generation_ms, "posthoc_collection_wall_ms": (time.perf_counter() - started) * 1000})
            if (offset // config["batch_size"]) % 16 == 0 or offset + len(batch) == len(items):
                print(f"Collected {min(offset + len(batch), len(items))}/{len(items)} puzzles", flush=True)
        destination = root / "results/trajectories" / manifest["run_id"]
        destination.mkdir(parents=True)
        write_level_records(destination / "levels.jsonl", all_records)
        write_outcomes(destination / "outcomes.jsonl", outcomes)
        export_parquet(destination / "levels.parquet", all_records)
        manifest.update(status="passed", artifact_sha256=hashes, trajectories=len(outcomes), records=len(all_records), total_levels=len(adapter.levels), unique_puzzles=len({o.puzzle_id for o in outcomes}), solved=sum(o.final_valid for o in outcomes), trajectory_directory=str(destination.relative_to(root)), batch_costs=costs, warmup_batches=1, output_equivalence="Every sample matches official shard output and final observed reconstruction", timing_scope="Generator totals are CUDA-synchronized after warmup. Posthoc capture includes decoding, transfer, labels and feature extraction. Per-level generation time is unknown; no online savings or overhead comparison established.")
    except Exception as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_manifest(root, manifest)
        raise
    return save_manifest(root, manifest)

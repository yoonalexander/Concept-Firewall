"""Independent observational label and saved-calibration audit for M3.

This audit never refits old probes or changes their test predictions. Its
checker deliberately does not call the production Sudoku parser/verifier.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import pickle

from .artifacts import sha256_file, verified_artifacts
from .probes import LinearProbe, feature_vector
from .provenance import new_manifest, save_manifest


def independent_cells(text: str) -> tuple[int, ...] | None:
    if not isinstance(text, str):
        return None
    compact = "".join(char for char in text if char not in " \t\r\n\v\f")
    if any(char not in "0123456789._|" for char in compact):
        return None
    if "|" in compact:
        parts = compact.split("|")
        if len(parts) != 9 or any(len(part) != 9 for part in parts):
            return None
        compact = "".join(parts)
    if len(compact) != 81:
        return None
    return tuple(int(char) if char in "123456789" else 0 for char in compact)


def independent_inspection(puzzle: str, output: str) -> dict:
    clues, board = independent_cells(puzzle), independent_cells(output)
    if clues is None:
        raise ValueError("Source puzzle is malformed")
    if board is None:
        return {"valid": False, "malformed": True, "blank_count": None, "changed_clues": [], "conflict_witnesses": []}
    units = [(f"row {r+1}", tuple(r*9+c for c in range(9))) for r in range(9)]
    units += [(f"column {c+1}", tuple(r*9+c for r in range(9))) for c in range(9)]
    units += [(f"box {br//3+1},{bc//3+1}", tuple((br+r)*9+bc+c for r in range(3) for c in range(3))) for br in (0,3,6) for bc in (0,3,6)]
    witnesses = []
    for name, indices in units:
        given = [clues[index] for index in indices if clues[index]]
        if len(set(given)) != len(given):
            raise ValueError("Source puzzle contains contradictory clues")
        values = [board[index] for index in indices]
        duplicates = sorted(digit for digit,count in Counter(v for v in values if v).items() if count > 1)
        if duplicates:
            witnesses.append({"unit": name, "values": values, "duplicate_digits": duplicates})
    changed = [{"row": i//9+1, "column": i%9+1, "clue": clue, "output": board[i]} for i,clue in enumerate(clues) if clue and board[i] != clue]
    blanks = board.count(0)
    return {"valid": not (blanks or changed or witnesses), "malformed": False, "blank_count": blanks, "changed_clues": changed, "conflict_witnesses": witnesses}


def digit_normalized_identity(puzzle: str, *, transpose: bool = False) -> str:
    """Limited symmetry diagnostic, not full Sudoku-isomorphism canonicalization."""
    cells = independent_cells(puzzle)
    if cells is None:
        raise ValueError("Malformed source puzzle")
    if transpose:
        cells = tuple(cells[c*9+r] for r in range(9) for c in range(9))
    mapping, normalized = {}, []
    for cell in cells:
        if cell and cell not in mapping:
            mapping[cell] = len(mapping)+1
        normalized.append(str(mapping[cell]) if cell else "0")
    return "".join(normalized)


def load_puzzles(root: Path) -> tuple[list, dict[str, str]]:
    verified_artifacts(root)
    with (root / "data/sudoku-hard/puzzles.pickle").open("rb") as stream:
        contexts = pickle.load(stream)  # Exactly the digest-verified public data.
    puzzles = {}
    for context in contexts:
        if len(context) != 91 or context[0] != 11 or context[-1] != 11:
            raise ValueError("Unexpected Sudoku context framing")
        if any(type(token) is not int or not 0 <= token <= 10 for token in context[1:-1]):
            raise ValueError("Unexpected Sudoku input token")
        puzzle = "".join("_123456789|"[token] for token in context[1:-1])
        cells = independent_cells(puzzle)
        if cells is None:
            raise ValueError("Malformed source puzzle")
        identity = hashlib.sha256("".join(map(str,cells)).encode("ascii")).hexdigest()
        if identity in puzzles:
            raise ValueError("Duplicate input identity requires explicit row mapping")
        puzzles[identity] = puzzle
    return contexts, puzzles


def run_audit(root: Path, protocol_path: Path) -> Path:
    import numpy as np
    from sklearn.metrics import roc_auc_score, log_loss
    from .schema import LevelState
    from .representations import extract_features

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = new_manifest(root, "m3-audit", {"protocol": protocol, "protocol_sha256": sha256_file(protocol_path)})
    protected = [root / protocol[key] for key in ("parent_collection", "parent_probes", "parent_splits")]
    protected += [root / "configs/probe_protocol.json"]
    before = {str(path.relative_to(root)): sha256_file(path) for path in protected}
    manifest["parent_sha256"] = before
    path = save_manifest(root, manifest)
    try:
        _, puzzles = load_puzzles(root)
        collection = json.loads((root / protocol["parent_collection"]).read_text())
        original = json.loads((root / protocol["parent_probes"]).read_text())
        split_file = root / protocol["parent_splits"]
        if sha256_file(split_file) != original["split_sha256"]:
            raise ValueError("Frozen original splits changed")
        splits = json.loads(split_file.read_text())
        flat = [identity for values in splits.values() for identity in values]
        if len(flat) != len(set(flat)) or set(flat) != set(puzzles):
            raise ValueError("Original partitions are not disjoint/exhaustive")
        directory = root / collection["trajectory_directory"]
        outcomes = [json.loads(line) for line in (directory / "outcomes.jsonl").read_text().splitlines()]
        outcome_map = {row["trajectory_id"]: row for row in outcomes}
        if len(outcome_map) != len(puzzles):
            raise ValueError("Outcome count/identity mismatch")
        baseline = json.loads((root / collection["baseline_manifest"]).read_text())
        with (root / baseline["raw_directory"] / "shard_0.pkl").open("rb") as stream:
            official = pickle.load(stream)  # Locally produced official evaluator output.
        if official["idxs"] != list(range(len(puzzles))) or len(official["hyps"]) != len(puzzles):
            raise ValueError("Official predictions are not exhaustive/in original row order")
        preserved = sorted((root / original["probe_directory"]).glob("*.json"))
        preserved += [directory / "levels.jsonl", directory / "outcomes.jsonl"]
        protected.extend(preserved)
        before.update({str(p.relative_to(root)):sha256_file(p) for p in preserved})
        final_by_puzzle = {identity: row["final_board"] for row in outcomes for identity in [row["puzzle_id"]]}
        _, ordered_puzzles = load_puzzles(root)
        if any(final_by_puzzle[key] != prediction for key,prediction in zip(ordered_puzzles, official["hyps"])):
            raise ValueError("Official final predictions changed")
        names = ("input", "decoded", "latent", "input_decoded", "input_decoded_latent", "codes", "shuffled_latent")
        levels = (protocol["primary_level"], protocol["secondary_level"], 12)
        models = {(level,name): LinearProbe.load(root / original["probe_directory"] / f"level-{level:02d}-{name}.json") for level in levels for name in names}
        raw = {(level,name): {} for level in levels for name in names}
        parent_predictions = {level: json.loads((root / original["probe_directory"] / f"level-{level:02d}-test_predictions.json").read_text()) for level in levels}
        selected, diagnostics, counts = {}, {}, Counter()
        manual = {}
        expected_indices = {row["trajectory_id"]: 0 for row in outcomes}
        with (directory / "levels.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                key, level = row["puzzle_id"], row["level"]
                outcome = outcome_map[row["trajectory_id"]]
                expected_indices[row["trajectory_id"]] += 1
                if level != expected_indices[row["trajectory_id"]] or key != outcome["puzzle_id"]:
                    raise ValueError("Trajectory levels/identity mismatch")
                inspection = independent_inspection(puzzles[key], row["predicted_board"])
                if inspection["valid"] != row["current_valid"]:
                    raise ValueError("Independent current label mismatch")
                if level == 12 and (inspection["valid"] != outcome["final_valid"] or row["predicted_board"] != outcome["final_board"]):
                    raise ValueError("Independent final label mismatch")
                counts["records"] += 1
                counts["malformed_records"] += inspection["malformed"]
                counts[f"level_{level}_valid"] += inspection["valid"]
                category = "malformed" if inspection["malformed"] else ("final_success" if level == 12 and inspection["valid"] else ("final_failure" if level == 12 else ("intermediate" if level == 6 else None)))
                if category is not None and category not in manual:
                    manual[category] = {"puzzle_id": key, "trajectory_id": row["trajectory_id"], "level": level, "puzzle": puzzles[key], "output": row["predicted_board"], "inspection": inspection}
                if level in levels:
                    selected[key,level] = row
                    state = LevelState(row["run_id"], key, row["trajectory_id"], level, row["codes_prefix"], row["predicted_board"], row["pooled_latent"])
                    recomputed = extract_features(state, puzzles[key])
                    if dict(recomputed) != row["features"]:
                        raise ValueError("Persisted features differ from current prefix-only extraction")
                    for name in names:
                        probe = models[level,name]
                        feature_names, values = feature_vector(row["features"], row["codes_prefix"], name)
                        if feature_names != probe.names:
                            raise ValueError("Probe feature schema mismatch")
                        score = probe.intercept + float(np.dot(probe.coefficient, (np.asarray(values)-probe.mean)/probe.scale))
                        raw[level,name][key] = score
        if any(value != 12 for value in expected_indices.values()) or counts["records"] != collection["records"]:
            raise ValueError("Missing full-depth records")
        for level in levels:
            prediction = parent_predictions[level]
            keys = prediction["puzzle_ids"]
            y = np.asarray(prediction["failure"])
            if set(keys) != set(splits["test"]) or any(y[i] != int(not outcome_map[selected[key,level]["trajectory_id"]]["final_valid"]) for i,key in enumerate(keys)):
                raise ValueError("Failure orientation or test identities differ")
            for name in names:
                probe = models[level,name]
                scores = np.asarray([raw[level,name][key] for key in keys])
                calibrated = 1/(1+np.exp(-np.clip(probe.calibration_intercept+probe.calibration_coefficient*scores, -700,700)))
                recorded = np.asarray(prediction["probabilities"][name])
                if not np.allclose(calibrated, recorded, atol=1e-12, rtol=1e-12):
                    raise ValueError("Saved test probabilities do not match raw-score reconstruction")
                partitions = {}
                for part in ("train", "validation", "calibration", "test"):
                    pkeys = splits[part]
                    py = np.asarray([int(not outcome_map[selected[key,level]["trajectory_id"]]["final_valid"]) for key in pkeys])
                    ps = np.asarray([raw[level,name][key] for key in pkeys])
                    cp = 1/(1+np.exp(-np.clip(probe.calibration_intercept+probe.calibration_coefficient*ps,-700,700)))
                    partitions[part] = {"raw_auroc": float(roc_auc_score(py,ps)), "calibrated_auroc": float(roc_auc_score(py,cp)), "calibrated_log_loss": float(log_loss(py,cp))}
                diagnostics[f"{level}:{name}"] = {"calibration_slope": probe.calibration_coefficient, "ranking_reversed": probe.calibration_coefficient < 0, "partitions": partitions}
        # Group a limited, explicitly documented symmetry family across development folds.
        symmetry = {key: min(digit_normalized_identity(puzzle), digit_normalized_identity(puzzle,transpose=True)) for key,puzzle in puzzles.items()}
        groups = {}
        for key,signature in symmetry.items():
            groups.setdefault(signature,[]).append(key)
        overlap = [values for values in groups.values() if len(values)>1]
        development = sorted(identity for name in protocol["development_partitions"] for identity in splits[name])
        destination = root / "results/probes" / manifest["run_id"]
        destination.mkdir(parents=True)
        arrays = {"puzzle_ids": np.asarray(development), "groups": np.asarray([hashlib.sha256(symmetry[key].encode()).hexdigest() for key in development]), "y": np.asarray([int(not outcome_map[selected[key,6]["trajectory_id"]]["final_valid"]) for key in development])}
        for level in (protocol["primary_level"],protocol["secondary_level"]):
            rows = [selected[key,level] for key in development]
            for family in ("decoded", "input_decoded", "latent"):
                arrays[f"level{level}_{family}"] = np.asarray([feature_vector(row["features"],row["codes_prefix"],family)[1] for row in rows],dtype=np.float32)
            arrays[f"level{level}_codes"] = np.asarray([[code for codes in row["codes_prefix"] for code in codes] for row in rows],dtype=np.int64)
            arrays[f"level{level}_boards"] = np.asarray([row["predicted_board"] for row in rows])
        data_path = destination / "development.npz"
        np.savez_compressed(data_path, **arrays)
        if before != {str(p.relative_to(root)): sha256_file(p) for p in protected}:
            raise ValueError("Protected original evidence changed")
        manifest.update(status="passed", label_audit=dict(counts), final_failures=sum(not row["final_valid"] for row in outcomes), calibration=diagnostics, manual_cases=manual, limited_symmetry_duplicate_groups=overlap, symmetry_limitations="digit renaming and transpose only; no full row/column/band/stack isomorphism audit", development_directory=str(destination.relative_to(root)), development_sha256=sha256_file(data_path), development_puzzles=len(development), excluded_original_test_puzzles=len(splits["test"]), original_artifacts_unchanged=True)
        save_manifest(root, manifest)
        write_audit_report(root,manifest)
        return path
    except Exception as error:
        manifest.update(status="failed",error=f"{type(error).__name__}: {error}")
        save_manifest(root,manifest)
        raise


def write_audit_report(root: Path, manifest: dict) -> Path:
    target = root / "results/reports" / f"{manifest['run_id']}.md"
    lines = ["# M3 label and calibration audit", "", f"Manifest: `results/manifests/{manifest['run_id']}.json`.", "", f"Independent checker matched all {manifest['label_audit']['records']} current labels and all 2,000 final outcomes/official predictions. Failures are positive (1). Original protected evidence is unchanged.", "", "| Level | Family | Calibration slope | Raw test AUROC | Calibrated test AUROC |", "|---:|---|---:|---:|---:|"]
    for name,result in manifest["calibration"].items():
        level,family=name.split(":")
        scores=result["partitions"]["test"]
        lines.append(f"| {level} | {family} | {result['calibration_slope']:.5f} | {scores['raw_auroc']:.5f} | {scores['calibrated_auroc']:.5f} |")
    lines += ["", "Negative calibration slopes reverse raw-score ordering. They were fit on the original calibration partition, not selected using test outcomes. This is an observed weak/unstable calibration issue, not proof of a label-orientation bug. No original sign, threshold, model or reported metric was changed. Both members of the primary comparison must be inspected separately.", "", "## Agent case walkthrough inputs", "", "The following cases are selected deterministically by category for review, not a representative statistical sample or a human annotation study. Independent diagnostic witnesses are generated here; the accompanying follow-up report records the agent's case walkthrough."]
    for category,case in manifest["manual_cases"].items():
        lines += ["",f"### {category} — level {case['level']}","",f"Puzzle `{case['puzzle_id']}`; trajectory `{case['trajectory_id']}`.","", "```text", "INPUT:  "+case["puzzle"], "OUTPUT: "+case["output"], "```", "", "```json",json.dumps(case["inspection"],indent=2),"```"]
    lines += ["",f"Development-only artifact contains {manifest['development_puzzles']} puzzles; all {manifest['excluded_original_test_puzzles']} old test identities are excluded. Limited digit-renaming/transpose duplicate groups: {len(manifest['limited_symmetry_duplicate_groups'])}. Full Sudoku symmetry equivalence remains unaudited.", "", "The observed test set is audited diagnostically only. No fresh confirmation is implied. Method references: [calibration](https://scikit-learn.org/stable/modules/calibration.html), [evaluation partitions](https://scikit-learn.org/stable/modules/cross_validation.html).", ""]
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text("\n".join(lines),encoding="utf-8")
    return target

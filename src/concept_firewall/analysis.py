"""Descriptive full-depth correctness analysis, with explicit completeness gates."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from .artifacts import sha256_file
from .storage import read_level_records, read_outcomes


def load_complete_trajectories(root: Path, manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("mode") != "collection" or manifest.get("status") != "passed":
        raise ValueError("A passed collection manifest is required")
    directory = (root / manifest["trajectory_directory"]).resolve()
    if not directory.is_relative_to(root.resolve()):
        raise ValueError("Trajectory directory must be inside the project")
    records = read_level_records(directory / "levels.jsonl")
    outcomes = read_outcomes(directory / "outcomes.jsonl")
    if not outcomes or len(records) != manifest["records"] or len(outcomes) != manifest["trajectories"]:
        raise ValueError("Manifest counts do not match stored observations")
    expected = list(range(1, manifest["total_levels"] + 1))
    by_trajectory = defaultdict(list)
    labels = {}
    for outcome in outcomes:
        if outcome.run_id != manifest["run_id"] or outcome.trajectory_id in labels:
            raise ValueError("Outcome identity mismatch or duplicate")
        labels[outcome.trajectory_id] = outcome
    for record in records:
        if record.trajectory_id not in labels:
            raise ValueError("Level has no outcome")
        outcome = labels[record.trajectory_id]
        if record.run_id != outcome.run_id or record.puzzle_id != outcome.puzzle_id:
            raise ValueError("Level/outcome puzzle or run identity mismatch")
        by_trajectory[record.trajectory_id].append(record)
    if set(by_trajectory) != set(labels):
        raise ValueError("An outcome has no observed levels")
    for trajectory_id, rows in by_trajectory.items():
        rows.sort(key=lambda row: row.level)
        if [row.level for row in rows] != expected:
            raise ValueError("Every trajectory must have exactly all expected levels")
        for prior, later in zip(rows, rows[1:]):
            if prior.codes_prefix != later.codes_prefix[:-1]:
                raise ValueError("Observed code prefix changed across levels")
        if rows[-1].current_valid != labels[trajectory_id].final_valid or rows[-1].predicted_board != labels[trajectory_id].final_board:
            raise ValueError("Final observed reconstruction and outcome disagree")
    if len({o.puzzle_id for o in outcomes}) != manifest["unique_puzzles"] or sum(o.final_valid for o in outcomes) != manifest["solved"]:
        raise ValueError("Manifest outcome summary differs from stored labels")
    return manifest, by_trajectory, labels


def summarize_trajectories(by_trajectory: dict) -> dict:
    count = len(by_trajectory)
    if not count:
        raise ValueError("No trajectories")
    levels = len(next(iter(by_trajectory.values())))
    categories = Counter()
    for rows in by_trajectory.values():
        states = [row.current_valid for row in rows]
        if all(states):
            categories["correct_at_every_level"] += 1
        elif not any(states):
            categories["wrong_at_every_level"] += 1
        elif states[-1]:
            categories["repaired_by_final_level"] += 1
        else:
            categories["became_wrong_by_final_level"] += 1
    per_level = []
    transitions = []
    for index in range(levels):
        rows = [trajectory[index] for trajectory in by_trajectory.values()]
        per_level.append({"level": index + 1, "trajectories": count, "unique_puzzles": len({row.puzzle_id for row in rows}), "correct": sum(row.current_valid for row in rows), "malformed": sum(row.features["decoded.malformed"] for row in rows)})
        if index:
            cells = Counter((trajectory[index - 1].current_valid, trajectory[index].current_valid) for trajectory in by_trajectory.values())
            transitions.append({"from": index, "to": index + 1, "wrong_wrong": cells[False, False], "wrong_right": cells[False, True], "right_wrong": cells[True, False], "right_right": cells[True, True]})
    return {"categories": dict(categories), "per_level": per_level, "transitions": transitions}


def analyze_trajectories(root: Path, manifest_path: Path) -> Path:
    manifest, grouped, labels = load_complete_trajectories(root, manifest_path)
    summary = summarize_trajectories(grouped)
    run_id = manifest["run_id"]
    directory = root / "results/reports"
    directory.mkdir(parents=True, exist_ok=True)
    report = directory / f"{run_id}-trajectory_analysis.md"
    lines = ["# Measured trajectory analysis", "", f"Run: `{run_id}`. Manifest: `{manifest_path.relative_to(root)}` (SHA-256 `{sha256_file(manifest_path)}`). Source snapshot hash: `{manifest['source_tree_sha256']}`.", "", f"Observed {len(labels)} trajectories / {manifest['unique_puzzles']} unique puzzles, each with {manifest['total_levels']} levels. Final clue-preserving valid completions: {manifest['solved']}/{len(labels)}. Every final output matches the official baseline.", "", "These are full-depth, post-hoc observations. No per-level generator timing, live lead time, intervention benefit or speedup was measured. A smoke subset does not establish statistical probe performance.", "", "| Level | Unique puzzles | Current correct | Malformed |", "|---:|---:|---:|---:|"]
    lines += [f"| {row['level']} | {row['unique_puzzles']} | {row['correct']}/{row['trajectories']} | {int(row['malformed'])} |" for row in summary["per_level"]]
    lines += ["", "Trajectory categories (exhaustive, mutually exclusive):", ""]
    lines += [f"- {name}: {value}" for name, value in sorted(summary["categories"].items())]
    lines += ["", "| Transition | Wrong → wrong | Wrong → right | Right → wrong | Right → right |", "|---|---:|---:|---:|---:|"]
    lines += [f"| {row['from']} → {row['to']} | {row['wrong_wrong']} | {row['wrong_right']} | {row['right_wrong']} | {row['right_right']} |" for row in summary["transitions"]]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    axis.plot([r["level"] for r in summary["per_level"]], [r["correct"] / r["trajectories"] for r in summary["per_level"]], marker="o")
    axis.set(xlabel="Hierarchy level (post-hoc reconstruction)", ylabel="Clue-preserving valid fraction", ylim=(-0.02, 1.02), title=f"NCM hard Sudoku: {manifest['unique_puzzles']} measured puzzles")
    axis.set_xticks(range(1, manifest["total_levels"] + 1))
    axis.grid(alpha=0.25)
    figure_path = root / "results/figures" / f"{run_id}-correctness.png"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_path, dpi=160)
    plt.close(figure)
    lines += ["", f"![Measured current correctness](../figures/{figure_path.name})", "", "Exact baseline command, artifact/data digests, upstream SHA, environment and batch costs are recorded in the linked collection/baseline manifests. Outcomes are eventual correctness labels; current incorrect states may self-correct.", ""]
    report.write_text("\n".join(lines), encoding="utf-8")
    report.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return report

"""Frozen grouped splits, train-only fitting and held-out probe comparisons."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .analysis import load_complete_trajectories
from .artifacts import sha256_file
from .probes import LinearProbe, feature_vector
from .provenance import new_manifest, save_manifest


def split_puzzles(puzzle_ids, *, seed: int, fractions: dict) -> dict[str, list[str]]:
    if set(fractions) != {"train", "validation", "calibration", "test"} or abs(sum(fractions.values()) - 1) > 1e-10 or any(v <= 0 for v in fractions.values()):
        raise ValueError("Four positive partition fractions must sum to one")
    ordered = sorted(set(puzzle_ids), key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    result, start = {}, 0
    for name in ("train", "validation", "calibration", "test"):
        end = len(ordered) if name == "test" else start + int(len(ordered) * fractions[name])
        result[name] = ordered[start:end]
        start = end
    if any(not ids for ids in result.values()):
        raise ValueError("Too few unique puzzles for four nonempty partitions")
    return result


def probability_metrics(y, probabilities, threshold: float) -> dict:
    import numpy as np
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    y, probabilities = np.asarray(y), np.asarray(probabilities)
    if not len(y) or not np.all(np.isfinite(probabilities)) or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Metrics require nonempty finite probabilities in [0,1]")
    both = len(np.unique(y)) == 2
    flagged = probabilities > threshold
    return {"samples": len(y), "failures": int(y.sum()), "failure_prevalence": float(y.mean()), "auroc": float(roc_auc_score(y, probabilities)) if both else None, "average_precision": float(average_precision_score(y, probabilities)) if both else None, "brier": float(brier_score_loss(y, probabilities)), "threshold": threshold, "fpr": float(flagged[y == 0].mean()) if np.any(y == 0) else None, "recall": float(flagged[y == 1].mean()) if np.any(y == 1) else None}


def _cluster_bootstrap(y, predictions: dict, puzzle_ids, *, count: int, seed: int) -> dict:
    import numpy as np
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    unique = sorted(set(puzzle_ids))
    indices = {key: np.flatnonzero(np.asarray(puzzle_ids) == key) for key in unique}
    scores = {name: [] for name in predictions}
    paired = []
    for _ in range(count):
        sampled = np.concatenate([indices[unique[i]] for i in rng.integers(len(unique), size=len(unique))])
        if len(np.unique(y[sampled])) < 2:
            continue
        current = {name: float(roc_auc_score(y[sampled], probabilities[sampled])) for name, probabilities in predictions.items()}
        for name, value in current.items():
            scores[name].append(value)
        paired.append(current["input_decoded_latent"] - current["input_decoded"])
    def interval(values):
        return list(map(float, np.quantile(values, [0.025, 0.975]))) if values else None
    return {"auroc_95_percentile_intervals": {name: interval(values) for name, values in scores.items()}, "paired_incremental_auroc_95_interval": interval(paired), "valid_replicates": len(paired), "requested_replicates": count}


def train_probes(root: Path, collection_path: Path, protocol_path: Path) -> Path:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    collection, grouped, outcomes = load_complete_trajectories(root, collection_path)
    if collection.get("reconstruction_contract") != "full-cumulative-prefix-v2":
        raise ValueError("Probe evaluation requires full-size cumulative prefix reconstructions, not native short z_levels")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    splits = split_puzzles([o.puzzle_id for o in outcomes.values()], seed=protocol["split_seed"], fractions=protocol["fractions"])
    manifest = new_manifest(root, "probes", {"collection_manifest": str(collection_path.relative_to(root)), "protocol": protocol, "protocol_sha256": sha256_file(protocol_path)})
    save_manifest(root, manifest)
    destination = root / "results/probes" / manifest["run_id"]
    destination.mkdir(parents=True)
    # Freeze exact identities before fitting any transform, model or calibration.
    split_path = root / "results/manifests" / f"{manifest['run_id']}-splits.json"
    split_path.write_text(json.dumps(splits, indent=2) + "\n", encoding="utf-8")
    manifest["split_manifest"] = str(split_path.relative_to(root))
    manifest["split_sha256"] = sha256_file(split_path)
    ids = sorted(grouped)
    y = np.asarray([int(not outcomes[key].final_valid) for key in ids])
    partitions = {name: np.asarray([i for i,key in enumerate(ids) if outcomes[key].puzzle_id in set(puzzles)]) for name,puzzles in splits.items()}
    counts = {name: {"trajectories": len(index), "unique_puzzles": len(splits[name]), "failures": int(y[index].sum()), "successes": int(len(index)-y[index].sum())} for name,index in partitions.items()}
    manifest["partition_counts"] = counts
    try:
        minimum = protocol["minimum_each_class_per_partition"]
        if any(min(count["failures"], count["successes"]) < minimum for count in counts.values()):
            raise ValueError(f"Insufficient outcome diversity for the frozen protocol: {counts}")
        results = []
        train, validation, calibration, test = (partitions[name] for name in ("train", "validation", "calibration", "test"))
        with threadpool_limits(limits=1):
            for level in range(1, collection["total_levels"] + 1):
                rows = [grouped[key][level - 1] for key in ids]
                predictions, metrics = {}, {}
                for family in protocol["models"]:
                    export = None
                    if family in ("prevalence", "level_only"):
                        calibrated = np.full(len(ids), y[train].mean())
                        selected_C = None
                    else:
                        vectors = [feature_vector(row.features, row.codes_prefix, family) for row in rows]
                        names = vectors[0][0]
                        if any(v[0] != names for v in vectors):
                            raise ValueError("Feature dimensions differ across observations")
                        x = np.asarray([v[1] for v in vectors])
                        scaler = StandardScaler().fit(x[train])
                        scaled = scaler.transform(x)
                        labels = y[train].copy()
                        if family == "shuffled_latent":
                            np.random.default_rng(protocol["split_seed"] + level).shuffle(labels)
                        candidates = []
                        for C in protocol["regularization_C"]:
                            model = LogisticRegression(C=C, solver="liblinear", max_iter=2000, random_state=protocol["split_seed"]).fit(scaled[train], labels)
                            if np.any(model.n_iter_ >= 2000):
                                raise RuntimeError("Logistic regression failed to converge")
                            candidates.append((log_loss(y[validation], model.predict_proba(scaled[validation])[:, 1]), C, model))
                        _, selected_C, model = min(candidates, key=lambda candidate: (candidate[0], candidate[1]))
                        raw_scores = model.decision_function(scaled)
                        calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000).fit(raw_scores[calibration, None], y[calibration])
                        calibrated = calibrator.predict_proba(raw_scores[:, None])[:, 1]
                        export = LinearProbe(family, level, names, tuple(scaler.mean_), tuple(scaler.scale_), tuple(model.coef_[0]), float(model.intercept_[0]), float(calibrator.coef_[0, 0]), float(calibrator.intercept_[0]))
                        (destination / f"level-{level:02d}-{family}.json").write_text(json.dumps({"schema_version": 1, **asdict(export)}, indent=2) + "\n", encoding="utf-8")
                    negative_scores = calibrated[calibration][y[calibration] == 0]
                    threshold = float(np.quantile(negative_scores, 1-protocol["false_positive_budget"], method="higher"))
                    predictions[family] = calibrated[test]
                    metrics[family] = {**probability_metrics(y[test], calibrated[test], threshold), "selected_C": selected_C}
                    # Explicit reliability bins, including empty bins, for inspection.
                    bins = []
                    for index in range(10):
                        mask = np.minimum((calibrated[test] * 10).astype(int), 9) == index
                        bins.append({"lower": index / 10, "upper": (index+1) / 10, "count": int(mask.sum()), "mean_probability": float(calibrated[test][mask].mean()) if mask.any() else None, "failure_fraction": float(y[test][mask].mean()) if mask.any() else None})
                    metrics[family]["calibration_bins"] = bins
                bootstrap = _cluster_bootstrap(y[test], predictions, [outcomes[ids[i]].puzzle_id for i in test], count=protocol["bootstrap_replicates"], seed=protocol["bootstrap_seed"])
                results.append({"level": level, "post_generation_only": level == collection["total_levels"], "metrics": metrics, "bootstrap": bootstrap})
                (destination / f"level-{level:02d}-test_predictions.json").write_text(json.dumps({"puzzle_ids": [outcomes[ids[i]].puzzle_id for i in test], "failure": y[test].tolist(), "probabilities": {name: p.tolist() for name,p in predictions.items()}}, indent=2) + "\n", encoding="utf-8")
                print(f"Evaluated frozen probes at level {level}/{collection['total_levels']}", flush=True)
        manifest.update(status="passed", collection_sha256=sha256_file(collection_path), artifact_sha256=collection["artifact_sha256"], results=results, probe_directory=str(destination.relative_to(root)))
        save_manifest(root, manifest)
        return write_probe_report(root, manifest)
    except Exception as error:
        manifest.update(status="failed", error=f"{type(error).__name__}: {error}")
        save_manifest(root, manifest)
        raise


def write_probe_report(root: Path, manifest: dict) -> Path:
    protocol = manifest["configuration"]["protocol"]
    primary = manifest["results"][protocol["primary_level"] - 1]
    metrics = primary["metrics"]
    difference = metrics["input_decoded_latent"]["auroc"] - metrics["input_decoded"]["auroc"]
    lines = ["# Initial held-out probe evaluation", "", f"Run `{manifest['run_id']}`; exact command, code hash, artifact hashes and full metrics: `results/manifests/{manifest['run_id']}.json`.", "", "The frozen four-way split carves up the public official test dataset. These are internal held-out results, not an untouched official benchmark. Exact duplicate puzzle identities stay together; Sudoku symmetries were not audited. One deterministic trajectory per puzzle supports between-puzzle prediction only.", "", f"Primary comparison declared before fitting: level {protocol['primary_level']}, input+decoded+latent minus input+decoded AUROC. Observed difference: {difference:.4f}; paired puzzle bootstrap 95% percentile interval: {primary['bootstrap']['paired_incremental_auroc_95_interval']}.", "", "| Partition | Unique puzzles | Failures | Successes |", "|---|---:|---:|---:|"]
    lines += [f"| {name} | {count['unique_puzzles']} | {count['failures']} | {count['successes']} |" for name,count in manifest["partition_counts"].items()]
    lines += ["", "Training-only standardization and regularized linear fitting; validation log-loss chooses C. Platt calibration and the empirical 5% negative-score threshold use calibration puzzles only. Test puzzles do not fit or select any parameter. Test FPR may exceed 5%; this is not a population guarantee. Level-only is constant, identical to training prevalence.", "", "| Level | Model | AUROC | AUROC 95% CI | Average precision | Brier | FPR | Recall |", "|---:|---|---:|---|---:|---:|---:|---:|"]
    for row in manifest["results"]:
        for family,m in row["metrics"].items():
            interval = row["bootstrap"]["auroc_95_percentile_intervals"][family]
            lines.append(f"| {row['level']} | {family} | {m['auroc']:.4f} | [{interval[0]:.4f}, {interval[1]:.4f}] | {m['average_precision']:.4f} | {m['brier']:.4f} | {m['fpr']:.4f} | {m['recall']:.4f} |")
    lines += ["", "Average precision is the non-interpolated PR summary, not trapezoidal PR area. Confidence intervals resample puzzle identities; models are not refitted in each bootstrap. Secondary levels/model comparisons are exploratory without multiplicity adjustment. Level 12 is post-generation diagnosis and cannot establish early prevention. Reliability bins and test predictions are retained for inspection.", "", "The latent probe alone does not identify conditional recovery, causation or safety. No online intervention, savings or actual per-level time-to-detection is established. A nonsignificant primary comparison is a valid negative result; no further phases are automatically authorized by a secondary peak.", ""]
    target = root / "results/reports" / f"{manifest['run_id']}-probe_evaluation.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target

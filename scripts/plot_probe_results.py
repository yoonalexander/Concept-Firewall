"""Render measured probe discrimination and calibration without refitting."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("--manifest", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
if manifest.get("status") != "passed" or manifest.get("mode") != "probes":
    raise ValueError("Completed measured probe run required")
primary_level = manifest["configuration"]["protocol"]["primary_level"]
primary = next(row for row in manifest["results"] if row["level"] == primary_level)
figure, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
families = {"decoded": "Decoded board", "latent": "Pooled latent", "input_decoded": "Input + decoded", "input_decoded_latent": "Input + decoded + latent"}
rows = [row for row in manifest["results"] if not row["post_generation_only"]]
for family,label in families.items():
    line, = axes[0].plot([r["level"] for r in rows], [r["metrics"][family]["auroc"] for r in rows], marker="o", markersize=3, label=label)
    intervals = [r["bootstrap"]["auroc_95_percentile_intervals"][family] for r in rows]
    axes[0].fill_between([r["level"] for r in rows], [interval[0] for interval in intervals], [interval[1] for interval in intervals], color=line.get_color(), alpha=.08)
    bins = [b for b in primary["metrics"][family]["calibration_bins"] if b["count"]]
    axes[1].plot([b["mean_probability"] for b in bins], [b["failure_fraction"] for b in bins], marker="o", label=label)
axes[0].axhline(.5, color="black", linestyle="--", linewidth=1, label="Chance")
axes[0].axvline(primary_level, color="gray", linestyle=":", linewidth=1)
axes[0].set(xlabel="Hierarchy level", ylabel="Held-out failure AUROC", ylim=(.2,.9), title="400 held-out puzzles; pointwise 95% bootstrap bands")
axes[0].set_xticks(range(1,12))
axes[0].legend(fontsize=8, loc="upper left")
axes[1].plot([0,1], [0,1], color="gray", linestyle="--", linewidth=1)
axes[1].set(xlabel="Mean predicted failure probability", ylabel="Observed failure fraction", xlim=(0,1), ylim=(0,1), title=f"Level {primary_level} test reliability (10 fixed bins)")
axes[1].legend(fontsize=8, loc="lower right")
for axis in axes:
    axis.grid(alpha=.15)
figure.suptitle("Concept Firewall: initial pooled-latent probes do not improve the primary comparison", fontsize=11)
path = root / "results/figures" / f"{manifest['run_id']}-probe_results.png"
path.parent.mkdir(parents=True, exist_ok=True)
figure.savefig(path, dpi=160)
plt.close(figure)
print(path)

"""Portable linear probes with an explicit current-level feature whitelist."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path

from .representations import extract_features
from .schema import LevelState

DECODED = ("filled_cells", "clue_violations", "row_conflicts", "column_conflicts", "box_conflicts", "malformed", "complete", "current_valid")


def feature_vector(features, codes_prefix, family: str) -> tuple[tuple[str, ...], tuple[float, ...]]:
    groups = {
        "input": ("input",), "decoded": ("decoded",), "codes": ("codes",),
        "latent": ("latent",), "shuffled_latent": ("latent",),
        "input_decoded": ("input", "decoded"),
        "input_decoded_latent": ("input", "decoded", "latent"),
    }
    if family not in groups:
        raise ValueError(f"Unsupported feature family: {family}")
    values = {}
    for group in groups[family]:
        if group == "input":
            values["input.clue_count"] = features["input.clue_count"]
            for index in range(81):
                cell = features[f"input.cell.{index:02d}"]
                if cell not in range(10):
                    raise ValueError("Raw input cell feature must be a digit in [0,9]")
                for digit in range(10):
                    values[f"input.cell.{index:02d}.is.{digit}"] = float(cell == digit)
        elif group == "decoded":
            values.update({f"decoded.{name}": features[f"decoded.{name}"] for name in DECODED})
        elif group == "latent":
            components = {k:v for k,v in features.items() if k.startswith("latent.component.")}
            if not components:
                raise ValueError("Pooled latent components are unavailable")
            values.update(components)
        elif group == "codes":
            current = codes_prefix[-1]
            if any(not 0 <= code < 16 for code in current):
                raise ValueError("Expected reviewed 16-entry hard-Sudoku codebook")
            values.update({f"codes.current.frequency.{code:02d}": current.count(code) / len(current) for code in range(16)})
    names = tuple(sorted(values))
    vector = tuple(float(values[name]) for name in names)
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("Probe features must be finite")
    return names, vector


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1 + exp)


@dataclass(frozen=True)
class LinearProbe:
    family: str
    level: int
    names: tuple[str, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coefficient: tuple[float, ...]
    intercept: float
    calibration_coefficient: float
    calibration_intercept: float

    def predict_failure_probability(self, state: LevelState, puzzle: str) -> float:
        if state.level != self.level:
            raise ValueError("Probe level does not match observed level")
        names, values = feature_vector(extract_features(state, puzzle), state.codes_prefix, self.family)
        if names != self.names:
            raise ValueError("Feature schema differs from the trained probe")
        score = self.intercept + math.fsum(coef * (value - mean) / scale for value, mean, scale, coef in zip(values, self.mean, self.scale, self.coefficient))
        return sigmoid(self.calibration_intercept + self.calibration_coefficient * score)

    @classmethod
    def load(cls, path: Path) -> LinearProbe:
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.pop("schema_version", None) != 1:
            raise ValueError("Unsupported probe schema")
        for key in ("names", "mean", "scale", "coefficient"):
            document[key] = tuple(document[key])
        result = cls(**document)
        if len({len(result.names), len(result.mean), len(result.scale), len(result.coefficient)}) != 1:
            raise ValueError("Probe dimensions differ")
        numbers = (*result.mean, *result.scale, *result.coefficient, result.intercept, result.calibration_coefficient, result.calibration_intercept)
        if any(not math.isfinite(value) for value in numbers) or any(value <= 0 for value in result.scale):
            raise ValueError("Invalid probe parameters")
        return result

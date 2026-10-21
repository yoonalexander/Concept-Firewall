"""Immutable, versioned records for full-depth offline trajectory collection.

``LevelState`` is the decision-time boundary: it contains only the observed
prefix and current reconstruction. Final labels and provenance live in a
separate ``TrajectoryOutcome``. ``checkpoint_sha256`` maps artifact names to
hashes, so a run can identify both the generator and tokenizer checkpoints.
Levels are one-based. Schema version 1 makes no claim of measured per-level
generation latency; unavailable timing must remain ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import re
from types import MappingProxyType
from typing import Mapping

from .sudoku_labels import parse_board


SCHEMA_VERSION = 1
FEATURE_VERSION = "sudoku-full-prefix-v2"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def puzzle_identity(puzzle: str) -> str:
    """Hash the actual canonical puzzle, independent of formatting or row ID."""
    canonical = "".join(str(cell) for cell in parse_board(puzzle))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _identifier(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty, trimmed string")


def _identity(run_id: str, puzzle_id: str, trajectory_id: str) -> None:
    _identifier(run_id, "run_id")
    _identifier(trajectory_id, "trajectory_id")
    if not isinstance(puzzle_id, str) or not _SHA256.fullmatch(puzzle_id):
        raise ValueError("puzzle_id must be the lowercase SHA256 of the canonical puzzle")


def _number(value: object, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def _prefix(level: int, codes_prefix: object) -> tuple[tuple[int, ...], ...]:
    if type(level) is not int or level < 1:
        raise ValueError("level must be a positive one-based integer")
    if not isinstance(codes_prefix, (tuple, list)) or len(codes_prefix) != level:
        raise ValueError("codes_prefix must contain exactly level observed levels")
    normalized = []
    for codes in codes_prefix:
        if not isinstance(codes, (tuple, list)) or not codes:
            raise ValueError("each code level must be a nonempty sequence")
        if any(type(code) is not int or code < 0 for code in codes):
            raise ValueError("codes must be nonnegative integers")
        normalized.append(tuple(codes))
    return tuple(normalized)


def _latent(values: object) -> tuple[float, ...]:
    if not isinstance(values, (tuple, list)):
        raise ValueError("pooled_latent must be a sequence")
    return tuple(_number(value, "pooled_latent") for value in values)


def _features(values: object) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError("features must be a mapping")
    result = {}
    for name, value in values.items():
        _identifier(name, "feature name")
        result[name] = _number(value, f"feature {name}")
    return MappingProxyType(result)


@dataclass(frozen=True)
class LevelState:
    """Only information observable after decoding the current prefix."""

    run_id: str
    puzzle_id: str
    trajectory_id: str
    level: int
    codes_prefix: tuple[tuple[int, ...], ...]
    predicted_board: str
    pooled_latent: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        _identity(self.run_id, self.puzzle_id, self.trajectory_id)
        object.__setattr__(self, "codes_prefix", _prefix(self.level, self.codes_prefix))
        object.__setattr__(self, "pooled_latent", _latent(self.pooled_latent))
        if not isinstance(self.predicted_board, str):
            raise ValueError("predicted_board must be a string, including malformed decodes")


@dataclass(frozen=True)
class LevelRecord:
    """Persisted current-level observations; no final outcome is included."""

    run_id: str
    puzzle_id: str
    trajectory_id: str
    level: int
    codes_prefix: tuple[tuple[int, ...], ...]
    predicted_board: str
    current_valid: bool
    features: Mapping[str, float] = field(default_factory=dict)
    pooled_latent: tuple[float, ...] = ()
    available_feature_version: str = FEATURE_VERSION
    generator_ms_incremental: float | None = None
    monitor_ms_incremental: float | None = None
    decode_ms_incremental: float | None = None

    def __post_init__(self) -> None:
        state = LevelState(
            self.run_id, self.puzzle_id, self.trajectory_id, self.level,
            self.codes_prefix, self.predicted_board, self.pooled_latent,
        )
        object.__setattr__(self, "codes_prefix", state.codes_prefix)
        object.__setattr__(self, "pooled_latent", state.pooled_latent)
        object.__setattr__(self, "features", _features(self.features))
        if type(self.current_valid) is not bool:
            raise ValueError("current_valid must be a boolean")
        if self.available_feature_version != FEATURE_VERSION:
            raise ValueError(f"unsupported feature version: {self.available_feature_version!r}")
        for name in ("generator_ms_incremental", "monitor_ms_incremental", "decode_ms_incremental"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _number(value, name, nonnegative=True))


@dataclass(frozen=True)
class TrajectoryOutcome:
    """Post-hoc labels and provenance, stored separately from level features."""

    run_id: str
    puzzle_id: str
    trajectory_id: str
    final_valid: bool
    configuration_id: str
    seed: int
    checkpoint_sha256: Mapping[str, str]
    upstream_commit: str
    final_board: str

    def __post_init__(self) -> None:
        _identity(self.run_id, self.puzzle_id, self.trajectory_id)
        _identifier(self.configuration_id, "configuration_id")
        if type(self.final_valid) is not bool:
            raise ValueError("final_valid must be a boolean")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if not isinstance(self.checkpoint_sha256, Mapping) or not self.checkpoint_sha256:
            raise ValueError("checkpoint_sha256 must map checkpoint names to SHA256 hashes")
        hashes = {}
        for name, digest in self.checkpoint_sha256.items():
            _identifier(name, "checkpoint name")
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError("checkpoint hashes must be lowercase SHA256 hex")
            hashes[name] = digest
        object.__setattr__(self, "checkpoint_sha256", MappingProxyType(hashes))
        if not isinstance(self.upstream_commit, str) or not _COMMIT.fullmatch(self.upstream_commit):
            raise ValueError("upstream_commit must be a full lowercase 40-character commit SHA")
        if not isinstance(self.final_board, str):
            raise ValueError("final_board must be a string, including malformed decodes")

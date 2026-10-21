"""Reference-free feature extraction from the explicit decision-time boundary.

These are deterministic descriptive features, not trained probes or evidence
that NCM representations predict eventual errors. Code IDs are categorical;
their arbitrary numeric values are not averaged. A supplied pooled latent must
already belong to the current level. This module never receives a trajectory,
reference completion, future suffix, or outcome record.
"""

from collections import Counter
import math
from types import MappingProxyType
from typing import Mapping

from .schema import LevelRecord, LevelState, puzzle_identity
from .sudoku_labels import parse_board, validate_sudoku


def extract_features(state: LevelState, puzzle: str) -> Mapping[str, float]:
    """Extract only prefix/current-board features for one known puzzle.

    The strict object type prevents accidentally passing a persisted row with
    extra label columns through a duck-typed feature interface.
    """
    if type(state) is not LevelState:
        raise TypeError("feature extraction requires an exact LevelState")
    if puzzle_identity(puzzle) != state.puzzle_id:
        raise ValueError("puzzle content does not match state.puzzle_id")
    clues = parse_board(puzzle)
    current = validate_sudoku(puzzle, state.predicted_board)
    codes = [code for level_codes in state.codes_prefix for code in level_codes]
    counts = Counter(codes)
    total = len(codes)
    entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
    result = {
        "input.clue_count": float(sum(cell != 0 for cell in clues)),
        "level.index": float(state.level),
        "codes.count": float(total),
        "codes.current_count": float(len(state.codes_prefix[-1])),
        "codes.unique_fraction": len(counts) / total,
        "codes.entropy_bits": entropy,
        "decoded.filled_cells": float(current.filled_cells),
        "decoded.clue_violations": float(current.clue_violations),
        "decoded.row_conflicts": float(current.row_conflicts),
        "decoded.column_conflicts": float(current.column_conflicts),
        "decoded.box_conflicts": float(current.box_conflicts),
        "decoded.malformed": float(current.malformed),
        "decoded.complete": float(current.is_complete),
        "decoded.current_valid": float(current.is_valid),
    }
    # The clue pattern is an input-only control and never includes a solution.
    result.update({f"input.clue_present.{index:02d}": float(cell != 0) for index, cell in enumerate(clues)})
    # Persist the raw input grid for a stronger categorical input-only control.
    result.update({f"input.cell.{index:02d}": float(cell) for index, cell in enumerate(clues)})
    if state.pooled_latent:
        values = state.pooled_latent
        # Scale before moments to avoid overflow for finite, unusually large inputs.
        scale = max(abs(value) for value in values)
        scaled = tuple(value / scale for value in values) if scale else values
        mean_scaled = math.fsum(scaled) / len(values)
        variance_scaled = math.fsum((value - mean_scaled) ** 2 for value in scaled) / len(values)
        result.update({
            "latent.mean": mean_scaled * scale,
            "latent.std": math.sqrt(variance_scaled) * scale,
            "latent.l2": math.hypot(*values),
        })
        result.update({f"latent.component.{index:04d}": value for index, value in enumerate(values)})
    if any(not math.isfinite(value) for value in result.values()):
        raise ValueError("feature aggregation produced a non-finite value")
    return MappingProxyType(result)


def make_level_record(
    state: LevelState,
    puzzle: str,
    *,
    generator_ms_incremental: float | None = None,
    monitor_ms_incremental: float | None = None,
    decode_ms_incremental: float | None = None,
) -> LevelRecord:
    """Create a label-free feature row plus its separate current-board label."""
    features = extract_features(state, puzzle)
    return LevelRecord(
        run_id=state.run_id, puzzle_id=state.puzzle_id,
        trajectory_id=state.trajectory_id, level=state.level,
        codes_prefix=state.codes_prefix, predicted_board=state.predicted_board,
        pooled_latent=state.pooled_latent,
        current_valid=validate_sudoku(puzzle, state.predicted_board).is_valid,
        features=features,
        generator_ms_incremental=generator_ms_incremental,
        monitor_ms_incremental=monitor_ms_incremental,
        decode_ms_incremental=decode_ms_incremental,
    )

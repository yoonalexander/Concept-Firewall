"""Immutable full-depth observations, without online intervention semantics."""

from __future__ import annotations

from typing import Callable, Sequence

from .schema import LevelState
from .upstream_adapter import NCMAdapter, ReconstructedLevel


def states_from_reconstructions(
    levels: Sequence[ReconstructedLevel], *, run_id: str,
    puzzle_ids: Sequence[str], trajectory_ids: Sequence[str],
    observer: Callable[[LevelState], None] | None = None,
) -> tuple[tuple[LevelState, ...], ...]:
    """Map immutable batch-level exports to sample-major decision-time states.

    The observer runs after full generation and reconstruction. It cannot stop
    generation, save compute, access mutable model tensors, or receive labels.
    Observer exceptions propagate and therefore cannot silently truncate data.
    """
    if not puzzle_ids or len(puzzle_ids) != len(trajectory_ids):
        raise ValueError("puzzle_ids and trajectory_ids must have the same nonzero length")
    if not levels:
        raise ValueError("at least one reconstructed level is required")
    batch_size = len(puzzle_ids)
    rows: list[list[LevelState]] = [[] for _ in range(batch_size)]
    for expected, level in enumerate(levels, start=1):
        if level.level != expected:
            raise ValueError("reconstructed levels must be contiguous and one-based")
        if any(len(value) != batch_size for value in (level.texts, level.codes_prefix_by_sample, level.pooled_latents)):
            raise ValueError("reconstruction batch does not match metadata")
        for sample in range(batch_size):
            state = LevelState(
                run_id=run_id, puzzle_id=puzzle_ids[sample],
                trajectory_id=trajectory_ids[sample], level=level.level,
                codes_prefix=level.codes_prefix_by_sample[sample],
                predicted_board=level.texts[sample], pooled_latent=level.pooled_latents[sample],
            )
            rows[sample].append(state)
            if observer is not None:
                observer(state)
    return tuple(tuple(row) for row in rows)


def collect_states(
    adapter: NCMAdapter, codes: object, *, run_id: str,
    puzzle_ids: Sequence[str], trajectory_ids: Sequence[str],
    observer: Callable[[LevelState], None] | None = None,
) -> tuple[tuple[LevelState, ...], ...]:
    """Reconstruct full-depth codes and expose only immutable current prefixes."""
    return states_from_reconstructions(
        adapter.reconstruct_levels(codes), run_id=run_id,
        puzzle_ids=puzzle_ids, trajectory_ids=trajectory_ids, observer=observer,
    )

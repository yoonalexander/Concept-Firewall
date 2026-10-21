"""Strict JSONL interchange and optional typed Parquet export.

Level observations and post-hoc outcomes must be written to separate files.
JSONL is dependency-free; Parquet requires the optional ``parquet`` extra.
Existing research files are protected unless ``overwrite=True`` is explicit.
"""

from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
from typing import Iterable, TypeVar

from .schema import LevelRecord, SCHEMA_VERSION, TrajectoryOutcome


Record = LevelRecord | TrajectoryOutcome
_RecordT = TypeVar("_RecordT", LevelRecord, TrajectoryOutcome)
_TYPES = {"level": LevelRecord, "outcome": TrajectoryOutcome}


def record_to_dict(record: Record) -> dict:
    """Return the versioned serialization object without mutable aliases."""
    if type(record) not in (LevelRecord, TrajectoryOutcome):
        raise TypeError("expected LevelRecord or TrajectoryOutcome")
    result = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "level" if type(record) is LevelRecord else "outcome",
    }
    for field in fields(record):
        value = getattr(record, field.name)
        if field.name in ("features", "checkpoint_sha256"):
            value = dict(value)
        elif field.name == "codes_prefix":
            value = [list(codes) for codes in value]
        elif field.name == "pooled_latent":
            value = list(value)
        result[field.name] = value
    return result


def record_from_dict(data: dict) -> Record:
    """Reject unknown versions, missing/extra fields, and invalid field values."""
    if not isinstance(data, dict):
        raise ValueError("record must be a JSON object")
    version = data.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {version!r}")
    kind = data.get("record_type")
    if not isinstance(kind, str) or kind not in _TYPES:
        raise ValueError(f"unknown record_type: {kind!r}")
    record_class = _TYPES[kind]
    expected = {field.name for field in fields(record_class)}
    supplied = set(data) - {"schema_version", "record_type"}
    if supplied != expected:
        raise ValueError(f"invalid record fields; missing={sorted(expected - supplied)}, extra={sorted(supplied - expected)}")
    return record_class(**{name: data[name] for name in expected})


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _read(path: str | Path, expected: type[_RecordT]) -> tuple[_RecordT, ...]:
    result = []
    seen = set()
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                data = json.loads(line, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
                record = record_from_dict(data)
                if type(record) is not expected:
                    raise ValueError("level records and outcomes must be stored separately")
                key = (record.run_id, record.puzzle_id, record.trajectory_id)
                if isinstance(record, LevelRecord):
                    key += (record.level,)
                if key in seen:
                    raise ValueError("duplicate record identity")
                seen.add(key)
                result.append(record)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}: line {line_number}: {exc}") from exc
    return tuple(result)


def _rows(records: Iterable[_RecordT], expected: type[_RecordT]) -> list[dict]:
    result = []
    seen = set()
    for record in records:
        if type(record) is not expected:
            raise TypeError("level records and outcomes must be stored separately")
        key = (record.run_id, record.puzzle_id, record.trajectory_id)
        if isinstance(record, LevelRecord):
            key += (record.level,)
        if key in seen:
            raise ValueError("duplicate record identity")
        seen.add(key)
        result.append(record_to_dict(record))
    return result


def _write(path: str | Path, records: Iterable[_RecordT], expected: type[_RecordT], overwrite: bool) -> None:
    rows = _rows(records, expected)
    # Serialize before opening the destination, so invalid input cannot truncate
    # an existing file even when the caller explicitly allows replacement.
    payload = "".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)


def write_level_records(path: str | Path, records: Iterable[LevelRecord], *, overwrite: bool = False) -> None:
    _write(path, records, LevelRecord, overwrite)


def read_level_records(path: str | Path) -> tuple[LevelRecord, ...]:
    return _read(path, LevelRecord)


def write_outcomes(path: str | Path, outcomes: Iterable[TrajectoryOutcome], *, overwrite: bool = False) -> None:
    _write(path, outcomes, TrajectoryOutcome, overwrite)


def read_outcomes(path: str | Path) -> tuple[TrajectoryOutcome, ...]:
    return _read(path, TrajectoryOutcome)


def export_parquet(path: str | Path, records: Iterable[Record], *, overwrite: bool = False) -> None:
    """Export homogeneous versioned records with stable Arrow field types.

    A separate call/file is required for outcomes. JSONL remains the canonical
    validated interchange; this export never joins final labels into features.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("Parquet export requires pyarrow; install concept-firewall[parquet]") from exc
    items = list(records)
    if not items:
        raise ValueError("Parquet export requires at least one typed record")
    expected = type(items[0])
    if expected not in (LevelRecord, TrajectoryOutcome):
        raise TypeError("expected LevelRecord or TrajectoryOutcome")
    rows = _rows(items, expected)
    common = [
        pa.field("schema_version", pa.int16(), nullable=False),
        pa.field("record_type", pa.string(), nullable=False),
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("puzzle_id", pa.string(), nullable=False),
        pa.field("trajectory_id", pa.string(), nullable=False),
    ]
    if expected is LevelRecord:
        specific = [
            pa.field("level", pa.int32(), nullable=False),
            pa.field("codes_prefix", pa.list_(pa.list_(pa.int64())), nullable=False),
            pa.field("predicted_board", pa.string(), nullable=False),
            pa.field("current_valid", pa.bool_(), nullable=False),
            pa.field("features", pa.map_(pa.string(), pa.float64()), nullable=False),
            pa.field("pooled_latent", pa.list_(pa.float64()), nullable=False),
            pa.field("available_feature_version", pa.string(), nullable=False),
            pa.field("generator_ms_incremental", pa.float64()),
            pa.field("monitor_ms_incremental", pa.float64()),
            pa.field("decode_ms_incremental", pa.float64()),
        ]
    else:
        specific = [
            pa.field("final_valid", pa.bool_(), nullable=False),
            pa.field("configuration_id", pa.string(), nullable=False),
            pa.field("seed", pa.int64(), nullable=False),
            pa.field("checkpoint_sha256", pa.map_(pa.string(), pa.string()), nullable=False),
            pa.field("upstream_commit", pa.string(), nullable=False),
            pa.field("final_board", pa.string(), nullable=False),
        ]
    table = pa.Table.from_pylist(rows, schema=pa.schema(common + specific))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb" if overwrite else "xb") as stream:
        pq.write_table(table, stream, compression="zstd")

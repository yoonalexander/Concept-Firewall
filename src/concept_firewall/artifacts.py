"""Narrow, immutable public artifact downloads with mandatory digest checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

UPSTREAM_COMMIT = "c70274273f489abc73832b2b98584a8483b6b203"
MODEL_REVISION = "d342ce8aaea58830eef3b8ad473664673e41f692"
DATA_REVISION = "6580ba41a4b0a976dde876fbe84d25327617b0e6"
# Hub paths are sudoku/hard, while the local evaluator folder is sudoku-hard.
FILES = (
    ("artifacts/sudoku-hard/generator.pt", "hazyresearch/ncm-checkpoints", MODEL_REVISION, "sudoku/hard/generator.pt", "9e0bfe44abc1ca3930b7a63cd56cd0b9564b95e29edfe12dd0903207b89df8b8", 102560203),
    ("artifacts/sudoku-hard/tokenizer.pt", "hazyresearch/ncm-checkpoints", MODEL_REVISION, "sudoku/hard/tokenizer.pt", "3bc6aecad8e15820f9d9bb09750e3c59bdf91ca953f1f11dbd109aaed1d80c0b", 59816209),
    ("data/sudoku-hard/puzzles.pickle", "datasets/hazyresearch/ncm-datasets", DATA_REVISION, "sudoku/hard/puzzles.pickle", "dd7b6763e5594094a1366ac8423f87fc9431056721c61df52ce3490023f17d5e", 372063),
    ("data/sudoku-hard/solutions.pickle", "datasets/hazyresearch/ncm-datasets", DATA_REVISION, "sudoku/hard/solutions.pickle", "b52de75f5e4642adca58b18967bcd4bbcafa699c61b21ac33ee0fd7389e0d576", 364063),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_artifacts(root: Path) -> dict[str, str]:
    hashes = {}
    for local, _, _, _, expected, size in FILES:
        path = root / local
        if not path.is_file():
            raise FileNotFoundError(f"Missing {local}; run concept-firewall download")
        actual = sha256_file(path)
        if path.stat().st_size != size or actual != expected:
            raise ValueError(f"Artifact digest/size mismatch: {local}")
        hashes[local] = actual
    return hashes


def download(root: Path) -> dict[str, str]:
    """Fetch only the four reviewed files; never use credentials or execute files."""
    for local, repo, revision, remote, expected, size in FILES:
        target = root / local
        if target.exists() and target.stat().st_size == size and sha256_file(target) == expected:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(
            f"https://huggingface.co/{repo}/resolve/{revision}/{remote}",
            headers={"User-Agent": "concept-firewall/0.1"},
        )
        print(f"Downloading {remote} ({size:,} bytes)", flush=True)
        with urllib.request.urlopen(request, timeout=120) as source, temporary.open("wb") as out:
            while chunk := source.read(1024 * 1024):
                out.write(chunk)
        if temporary.stat().st_size != size or sha256_file(temporary) != expected:
            raise ValueError(f"Downloaded artifact digest/size mismatch: {remote}")
        temporary.replace(target)
    hashes = verified_artifacts(root)
    destination = root / "results/manifests/artifacts.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"model_revision": MODEL_REVISION, "data_revision": DATA_REVISION, "sha256": hashes}, indent=2) + "\n", encoding="utf-8")
    return hashes

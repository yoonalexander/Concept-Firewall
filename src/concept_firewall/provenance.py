"""Local provenance and durable run manifests; no credentials are recorded."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

from .artifacts import UPSTREAM_COMMIT, sha256_file


def git_revision(root: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def require_upstream(root: Path) -> str:
    revision = git_revision(root / "third_party/ncm")
    if revision != UPSTREAM_COMMIT:
        raise ValueError(f"NCM revision is {revision!r}; expected {UPSTREAM_COMMIT}. Restore the pinned submodule.")
    changed = subprocess.run(["git", "-C", str(root / "third_party/ncm"), "status", "--porcelain"], capture_output=True, text=True)
    if changed.returncode or changed.stdout.strip():
        raise ValueError("NCM checkout is modified or cannot be checked; provenance requires unmodified pinned source")
    return revision


def source_hash(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted((root / "src").rglob("*.py")) + sorted((root / "configs").glob("*")) + [root / "pyproject.toml"]
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def environment() -> dict:
    packages = {}
    for name in ("torch", "numpy", "omegaconf", "hydra-core", "transformers", "pyarrow", "scikit-learn"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    result = {"python": sys.version, "platform": platform.platform(), "packages": packages}
    try:
        import torch
        result.update(torch_cuda=torch.version.cuda, cuda_available=torch.cuda.is_available())
        if torch.cuda.is_available():
            result["gpu"] = torch.cuda.get_device_name(0)
            result["gpu_memory_bytes"] = torch.cuda.get_device_properties(0).total_memory
    except ImportError:
        result.update(torch_cuda=None, cuda_available=False)
    return result


def new_manifest(root: Path, mode: str, configuration: dict) -> dict:
    digest = source_hash(root)
    snapshot = root / "results/source_snapshots" / f"{digest}.zip"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    if not snapshot.exists():
        files = sorted((root / "src").rglob("*.py")) + sorted((root / "configs").glob("*")) + [root / "pyproject.toml"]
        if (root / "requirements.lock").is_file():
            files.append(root / "requirements.lock")
        with zipfile.ZipFile(snapshot, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(root))
    return {
        "schema_version": "1.0", "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + mode,
        "mode": mode, "status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-m", "concept_firewall", *sys.argv[1:]],
        "code_revision": git_revision(root), "source_tree_sha256": digest,
        "source_snapshot": snapshot.relative_to(root).as_posix(), "source_snapshot_sha256": sha256_file(snapshot),
        "upstream_commit": UPSTREAM_COMMIT, "configuration": configuration,
        "environment": environment(), "claims": "Research measurements only; no intervention or safety effectiveness established.",
    }


def save_manifest(root: Path, manifest: dict) -> Path:
    target = root / "results/manifests" / (manifest["run_id"] + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target

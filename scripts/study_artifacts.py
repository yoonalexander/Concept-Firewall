"""Package or restore the retained Sudoku evidence; never include weights or secrets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile


DIRECTORIES = (
    "results/raw",
    "results/trajectories/20261021T015216719695Z-collection",
    "results/probes/20261021T015457393177Z-probes",
    "results/probes/20261023T121711278798Z-m3-audit",
    "results/probes/20261023T122529782263Z-m3-followup",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def inside(root: Path, name: str, directories=DIRECTORIES) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe archive path: {name}")
    if not any(name.startswith(prefix + "/") for prefix in directories):
        raise ValueError(f"Not a declared study artifact: {name}")
    target = root.joinpath(*relative.parts).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Path escapes checkout: {name}")
    return target


def pack(root: Path, archive: Path, inventory: Path, *, directories=DIRECTORIES) -> None:
    paths = []
    for directory in directories:
        folder = root / directory
        if not folder.is_dir():
            raise FileNotFoundError(folder)
        paths.extend(path for path in folder.rglob("*") if path.is_file())
    paths.sort()
    entries = []
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in paths:
            name = path.relative_to(root).as_posix()
            inside(root, name, directories)
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as source, output.open(info, "w") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            entries.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    record = {"schema_version": 1, "scope": "Retained evidence replay, not fresh model generation",
              "archive": archive.name, "archive_bytes": archive.stat().st_size,
              "archive_sha256": digest(archive), "files": entries,
              "excluded": ["weights and official dataset (use download)", "superseded short-prefix trajectories",
                           "superseded initial probes", "failed feature capture artifacts", "Python environment"]}
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "inventory": str(inventory), "files": len(entries),
                      "bytes": record["archive_bytes"], "sha256": record["archive_sha256"]}))


def restore(root: Path, archive: Path, inventory: Path, *, directories=DIRECTORIES) -> None:
    record = json.loads(inventory.read_text(encoding="utf-8"))
    if archive.stat().st_size != record["archive_bytes"] or digest(archive) != record["archive_sha256"]:
        raise ValueError("Archive size or SHA-256 mismatch")
    entries = {entry["path"]: entry for entry in record["files"]}
    if len(entries) != len(record["files"]):
        raise ValueError("Duplicate inventory path")
    with zipfile.ZipFile(archive) as source:
        if len(source.namelist()) != len(entries) or set(source.namelist()) != set(entries):
            raise ValueError("Archive contents do not match the inventory")
        # Validate every member and existing destination before writing anything.
        for name, entry in entries.items():
            target = inside(root, name, directories)
            info = source.getinfo(name)
            if info.file_size != entry["bytes"]:
                raise ValueError(f"Member size mismatch: {name}")
            value = hashlib.sha256()
            with source.open(name) as member:
                for chunk in iter(lambda: member.read(1024 * 1024), b""):
                    value.update(chunk)
            if value.hexdigest() != entry["sha256"]:
                raise ValueError(f"Member hash mismatch: {name}")
            if target.exists() and (not target.is_file() or digest(target) != entry["sha256"]):
                raise ValueError(f"Refusing to overwrite different existing content: {name}")
        for name, entry in entries.items():
            target = inside(root, name, directories)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(name) as member, target.open("xb") as output:
                shutil.copyfileobj(member, output, length=1024 * 1024)
            if digest(target) != entry["sha256"]:
                raise ValueError(f"Restoration hash mismatch: {name}")
    print(json.dumps({"status": "passed", "restored_or_verified_files": len(entries),
                      "archive_sha256": record["archive_sha256"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("pack", "restore"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, default=Path("results/manifests/sudoku_study_artifacts.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    action = pack if args.mode == "pack" else restore
    action(root, args.archive.resolve(), (root / args.inventory).resolve())


if __name__ == "__main__":
    main()

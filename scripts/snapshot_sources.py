"""Preserve uncommitted experiment source without creating a Git commit."""
from pathlib import Path
import json
import zipfile

from concept_firewall.artifacts import sha256_file
from concept_firewall.provenance import source_hash

root = Path(__file__).resolve().parents[1]
digest = source_hash(root)
destination = root / "results/source_snapshots" / f"{digest}.zip"
destination.parent.mkdir(parents=True, exist_ok=True)
files = sorted((root / "src").rglob("*.py")) + sorted((root / "configs").glob("*")) + [root / "pyproject.toml", root / "requirements.lock"]
if not destination.exists():
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root))
registry = root / "results/manifests/source_snapshots.json"
entries = json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else {}
entries[digest] = {"path": destination.relative_to(root).as_posix(), "archive_sha256": sha256_file(destination), "note": "Source-content hash covers Python package, configs and pyproject; environment snapshot also included. Repository has no commit yet."}
registry.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
print(destination)

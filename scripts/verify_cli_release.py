"""Inspect and install both release archives in fresh venvs (standard library).

Build first. Supply an offline wheelhouse containing setuptools>=68 for the
isolated sdist build. All commands run outside the checkout with PYTHONPATH unset.
"""

from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import tempfile
import zipfile


VERSION = "0.2.0"
SOURCE_FILES = {"pyproject.toml", "MANIFEST.in", "CLI_README.md", "CLI_RELEASE_NOTES.md",
                "THIRD_PARTY_NOTICES.md", "PKG-INFO", "examples/sudoku_demo.py",
                "scripts/test_installed_cli.py", "scripts/verify_cli_release.py",
                "tests/test_sudoku_labels.py", "tests/test_verified_solver.py"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_archives(wheel, sdist):
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        for name in wheel_names:
            parts = PurePosixPath(name).parts
            assert ".." not in parts and not name.startswith("/"), name
            assert (len(parts) == 2 and parts[0] == "concept_firewall" and name.endswith(".py")) or (
                len(parts) == 2 and parts[0] == f"concept_firewall-{VERSION}.dist-info"
                and parts[1] in {"METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD"}
            ), f"Unexpected wheel member: {name}"
        metadata = BytesParser().parsebytes(archive.read(f"concept_firewall-{VERSION}.dist-info/METADATA"))
        assert metadata["Version"] == VERSION and metadata["Requires-Python"] == ">=3.10"
        assert all("extra ==" in req for req in metadata.get_all("Requires-Dist", []))
        assert 'concept-firewall = concept_firewall.cli:main' in archive.read(
            f"concept_firewall-{VERSION}.dist-info/entry_points.txt").decode()

    with tarfile.open(sdist, "r:gz") as archive:
        source_names = []
        members = {}
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            assert path.parts[0] == f"concept_firewall-{VERSION}", member.name
            assert not path.is_absolute() and ".." not in path.parts, member.name
            assert member.isdir() or member.isfile(), f"Nonregular archive member: {member.name}"
            if member.isdir():
                continue
            name = str(PurePosixPath(*path.parts[1:]))
            assert name in SOURCE_FILES or name == "setup.cfg" or (
                name.startswith("src/concept_firewall/") and name.endswith(".py")
                and len(PurePosixPath(name).parts) == 3
            ) or (
                name.startswith("src/concept_firewall.egg-info/")
                and PurePosixPath(name).name in {"PKG-INFO", "SOURCES.txt", "dependency_links.txt",
                                               "entry_points.txt", "requires.txt", "top_level.txt"}
            ), f"Unexpected sdist member: {name}"
            source_names.append(name)
            members[name] = archive.extractfile(member).read()
        assert SOURCE_FILES <= set(source_names), SOURCE_FILES - set(source_names)
        # The wheel must contain the same Python sources as the tested sdist.
        with zipfile.ZipFile(wheel) as zipped:
            wheel_python = {name for name in wheel_names if name.startswith("concept_firewall/")}
            source_python = {name[4:] for name in source_names if name.startswith("src/concept_firewall/")}
            assert wheel_python == source_python
            for name in wheel_python:
                assert zipped.read(name) == members["src/" + name], name
    return {"wheel_members": wheel_names, "sdist_members": source_names,
            "source_wheel_python_identical": True, "allowlist_passed": True}, members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--python", action="append", required=True, help="Python interpreter; repeat for each version")
    parser.add_argument("--work-dir", type=Path, default=Path(".tmp/release-check"))
    parser.add_argument("--report", type=Path, default=Path("dist/cli-release-verification.json"))
    args = parser.parse_args()
    dist = args.dist.resolve()
    wheel = dist / f"concept_firewall-{VERSION}-py3-none-any.whl"
    sdist = dist / f"concept_firewall-{VERSION}.tar.gz"
    inventory, members = inspect_archives(wheel, sdist)
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=work))
    outside = run_dir / "outside-checkout"
    outside.mkdir()
    temp = run_dir / "temp"
    temp.mkdir()
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp),
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONUTF8="1")
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    test = outside / "test_installed_cli.py"
    demo = outside / "sudoku_demo.py"
    test.write_bytes(members["scripts/test_installed_cli.py"])
    demo.write_bytes(members["examples/sudoku_demo.py"])
    results = []

    def run(command):
        result = subprocess.run(list(map(str, command)), cwd=outside, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=300)
        if result.returncode:
            raise RuntimeError(f"Command failed: {command}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    for index, interpreter in enumerate(args.python):
        for kind, artifact in (("wheel", wheel), ("sdist", sdist)):
            venv = run_dir / f"python-{index}-{kind}"
            run([interpreter, "-m", "venv", venv])
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            install = [python, "-m", "pip", "install", "--no-index", "--no-cache-dir"]
            if kind == "wheel":
                install += ["--no-deps"]
            else:
                install += ["--find-links", args.wheelhouse.resolve()]
            install_log = run([*install, artifact])
            (run_dir / f"python-{index}-{kind}-install.log").write_text(install_log, encoding="utf-8")
            data = json.loads(run([python, "-I", test]))
            demo_output = json.loads(run([python, "-I", demo]))
            assert demo_output["rechecked_completion"]["is_valid"] is True
            data.update(artifact=artifact.name, demo_passed=True, pip_check=run([python, "-m", "pip", "check"]).strip())
            results.append(data)
            print(f"PASS {kind} Python {data['python']}: {data['checks_passed']} CLI checks + demo", flush=True)
    # Existing adversarial parsing tests also run from the sdist, without research deps.
    unit = outside / "tests"
    unit.mkdir()
    (unit / "test_sudoku_labels.py").write_bytes(members["tests/test_sudoku_labels.py"])
    run([python, "-I", "-m", "unittest", "discover", "-s", unit])
    tool_versions = {}
    for name in ("build", "setuptools", "wheel", "pip"):
        try:
            tool_versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    report = {"version": VERSION, "platform": platform.platform(), "build_tools": tool_versions,
              "artifacts": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
                            for path in (wheel, sdist)},
              "archive_inspection": inventory, "environments": results,
              "sdist_adversarial_parser_tests_passed": 26,
              "total_installed_command_checks": sum(item["checks_passed"] for item in results),
              "all_passed": True,
              "scope": "Classical Sudoku CLI only; no models, research experiments or learned firewall claims."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verification report: {args.report}", flush=True)


if __name__ == "__main__":
    main()

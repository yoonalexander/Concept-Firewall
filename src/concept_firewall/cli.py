"""Small explicit commands; future research gates have no pretend implementations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Concept Firewall: frozen NCM correctness research")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project checkout (default current directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect environment, CUDA and upstream revision without downloads")
    commands.add_parser("download", help="Download only pinned, hash-checked hard-Sudoku artifacts (~164 MB)")
    contract = commands.add_parser("v2-contract", help="Freeze V2 protocol and CPU-only prospective design calculation; no model runs")
    contract.add_argument("--protocol", type=Path, default=Path("configs/v2_study.json"))
    pilot = commands.add_parser("v2-pilot", help="Verify observed/control generation on frozen legacy pilot identities")
    pilot.add_argument("--protocol", type=Path, default=Path("configs/v2_study.json"))
    check = commands.add_parser("verify", help="Verify a Sudoku completion without ML dependencies")
    check.add_argument("--puzzle", required=True)
    check.add_argument("--board", required=True)
    for name in ("baseline", "collect"):
        sub = commands.add_parser(name, help="Run official baseline" if name == "baseline" else "Collect full-depth trajectories after matching baseline")
        sub.add_argument("--config", type=Path, default=Path("configs/sudoku_smoke.yaml"))
        if name == "collect":
            sub.add_argument("--baseline-manifest", type=Path, required=True)
    analyze = commands.add_parser("analyze", help="Describe measured trajectory correctness and transitions")
    analyze.add_argument("--manifest", type=Path, required=True)
    probes = commands.add_parser("train", help="Fit frozen grouped probes after real collection/equivalence gates")
    probes.add_argument("--manifest", type=Path, required=True)
    probes.add_argument("--protocol", type=Path, default=Path("configs/probe_protocol.json"))
    audit = commands.add_parser("audit", help="Independently audit old M3 labels, calibration and development boundaries")
    audit.add_argument("--protocol", type=Path, default=Path("configs/m3_followup.json"))
    followup = commands.add_parser("followup", help="Evaluate exactly two exploratory spatial representations on development puzzles only")
    followup.add_argument("--audit-manifest", type=Path, required=True)
    followup.add_argument("--protocol", type=Path, default=Path("configs/m3_followup.json"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "doctor":
            from .provenance import environment, git_revision
            from .artifacts import UPSTREAM_COMMIT
            print(json.dumps({"environment": environment(), "upstream_commit": git_revision(root / "third_party/ncm"), "expected_commit": UPSTREAM_COMMIT}, indent=2))
        elif args.command == "download":
            from .artifacts import download
            print(json.dumps(download(root), indent=2))
        elif args.command == "v2-contract":
            from .v2_protocol import freeze_contract
            print(freeze_contract(root, (root / args.protocol).resolve()))
        elif args.command == "v2-pilot":
            from .v2_observer import run_pilot
            print(run_pilot(root, (root / args.protocol).resolve()))
        elif args.command == "verify":
            from dataclasses import asdict
            from .sudoku_labels import validate_sudoku
            result = validate_sudoku(args.puzzle, args.board)
            print(json.dumps(asdict(result), indent=2))
            return 0 if result.is_valid else 1
        elif args.command in ("baseline", "collect"):
            from .runner import baseline, collect, read_configuration
            config = read_configuration(root, root / args.config)
            path = baseline(root, config) if args.command == "baseline" else collect(root, config, (root / args.baseline_manifest).resolve())
            print(path)
        elif args.command == "analyze":
            from .analysis import analyze_trajectories
            print(analyze_trajectories(root, (root / args.manifest).resolve()))
        elif args.command == "train":
            from .training import train_probes
            print(train_probes(root, (root / args.manifest).resolve(), (root / args.protocol).resolve()))
        elif args.command == "audit":
            from .diagnostics import run_audit
            print(run_audit(root, (root / args.protocol).resolve()))
        elif args.command == "followup":
            from .followup import run_followup
            print(run_followup(root, (root / args.audit_manifest).resolve(), (root / args.protocol).resolve()))
    except (ValueError, RuntimeError, OSError, ImportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0

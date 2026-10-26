"""Black-box contract checks; run with a clean environment's Python, outside src.

No test framework or research imports. Both installed entry points are exercised.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig


PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
SOLUTION = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"


def independent_check(puzzle, board):
    """Check a compact completion without the package's verifier or solver."""
    assert isinstance(board, str) and len(board) == 81
    assert all(char in "123456789" for char in board)
    assert all(clue == "0" or clue == value for clue, value in zip(puzzle, board))
    target = set("123456789")
    for index in range(9):
        assert set(board[index * 9:index * 9 + 9]) == target
        assert set(board[index::9]) == target
    for row in (0, 3, 6):
        for col in (0, 3, 6):
            assert {board[(row + r) * 9 + col + c] for r in range(3) for c in range(3)} == target


def main():
    import concept_firewall

    package_path = Path(concept_firewall.__file__).resolve()
    assert Path(sys.prefix).resolve() in package_path.parents, package_path
    assert sys.prefix != sys.base_prefix, "Run these checks inside a fresh venv"
    assert not sys.flags.optimize, "Assertions must be enabled"
    version = importlib.metadata.version("concept-firewall")
    assert version == concept_firewall.__version__ == "0.2.0"
    for requirement in importlib.metadata.requires("concept-firewall") or []:
        assert "extra ==" in requirement, f"Unexpected runtime dependency: {requirement}"
    forbidden = ("torch", "numpy", "scipy", "sklearn", "omegaconf", "hydra",
                 "transformers", "huggingface_hub", "regex", "sacrebleu",
                 "rouge_score", "pyarrow", "matplotlib", "triton")
    assert all(importlib.util.find_spec(name) is None for name in forbidden)
    installed = sorted(dist.metadata["Name"] for dist in importlib.metadata.distributions())
    assert not any(name.lower().startswith(("nvidia-", "cuda-")) for name in installed)

    console = Path(sysconfig.get_path("scripts")) / (
        "concept-firewall.exe" if os.name == "nt" else "concept-firewall"
    )
    assert console.is_file(), console
    prefixes = {"console": [str(console)], "module": [sys.executable, "-I", "-m", "concept_firewall"]}
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    checks = []

    def call(prefix, args, code, *, json_output=True):
        result = subprocess.run([*prefix, *args], capture_output=True, text=True, env=env,
                                encoding="utf-8", timeout=30)
        assert result.returncode == code, (args, result.returncode, result.stdout, result.stderr)
        if json_output:
            assert not result.stderr, result.stderr
            return json.loads(result.stdout)
        return result

    for entry, prefix in prefixes.items():
        def check(name, args, code, expected=None):
            data = call(prefix, args, code)
            for key, value in (expected or {}).items():
                assert data[key] == value, (name, key, data)
            if args[0] == "solve":
                if code == 0:
                    independent_check(args[args.index("--puzzle") + 1], data["board"])
                    assert data["verified"] is True
                else:
                    assert data["board"] is None and data["verified"] is False
            checks.append(f"{entry}:{name}")
            return data

        for args in (["--help"], ["verify", "--help"], ["solve", "--help"], ["--version"]):
            result = call(prefix, args, 0, json_output=False)
            assert not result.stderr and result.stdout
            if args == ["--version"]:
                assert result.stdout.strip() == "concept-firewall 0.2.0"
            checks.append(f"{entry}:{' '.join(args)}")

        check("valid", ["verify", "--puzzle", PUZZLE, "--board", SOLUTION], 0,
              {"is_valid": True, "is_complete": True, "filled_cells": 81, "errors": [],
               "clue_violations": 0, "row_conflicts": 0, "column_conflicts": 0, "box_conflicts": 0})
        check("incorrect", ["verify", "--puzzle", PUZZLE, "--board", "1" * 81], 1,
              {"is_valid": False, "is_complete": True, "row_conflicts": 72,
               "column_conflicts": 72, "box_conflicts": 72})
        alternative = SOLUTION.translate(str.maketrans("12", "21"))
        check("changed-clues", ["verify", "--puzzle", PUZZLE, "--board", alternative], 1,
              {"is_valid": False, "row_conflicts": 0, "column_conflicts": 0, "box_conflicts": 0})
        check("incomplete", ["verify", "--puzzle", PUZZLE, "--board", PUZZLE], 1,
              {"is_valid": False, "is_complete": False, "malformed": False})
        for board in ("bad input", SOLUTION[:-1], SOLUTION + "1", SOLUTION[:-1] + "１",
                      "|".join(SOLUTION), "Answer: " + SOLUTION):
            check(f"malformed-board-{len(checks)}", ["verify", "--puzzle", PUZZLE, "--board", board], 1,
                  {"is_valid": False, "malformed": True, "board": None})
        for puzzle in ("bad input", PUZZLE[:-1], "55" + "0" * 79):
            data = check(f"invalid-verify-puzzle-{len(checks)}",
                         ["verify", "--puzzle", puzzle, "--board", SOLUTION], 1, {"is_valid": False})
            assert any(error.startswith("invalid_puzzle:") for error in data["errors"])
            check(f"invalid-solve-puzzle-{len(checks)}",
                  ["solve", "--puzzle", puzzle, "--board", SOLUTION], 1,
                  {"status": "invalid_puzzle", "used_fallback": False, "search_nodes": 0})
        rows = "|".join(PUZZLE[i:i + 9] for i in range(0, 81, 9)).replace("0", "_")
        check("pipe-and-whitespace", ["verify", "--puzzle", rows, "--board", " \n".join(SOLUTION)], 0,
              {"is_valid": True})
        check("dots", ["verify", "--puzzle", PUZZLE.replace("0", "."), "--board", SOLUTION], 0,
              {"is_valid": True})
        nonunique = "".join("0" if char in "12" else char for char in SOLUTION)
        check("alternative-solution", ["verify", "--puzzle", nonunique, "--board", alternative], 0,
              {"is_valid": True})
        check("accepted-proposal", ["solve", "--puzzle", PUZZLE, "--board", SOLUTION, "--node-limit", "1"], 0,
              {"status": "accepted_proposal", "board": SOLUTION, "used_fallback": False, "search_nodes": 0})
        for proposal in (None, "1" * 81, "bad input", "0" * 81, alternative):
            args = ["solve", "--puzzle", PUZZLE]
            if proposal is not None:
                args += ["--board", proposal]
            check(f"fallback-{len(checks)}", args, 0,
                  {"status": "solved_exact", "board": SOLUTION, "used_fallback": True})
        check("complete-original", ["solve", "--puzzle", SOLUTION, "--node-limit", "1"], 0,
              {"status": "solved_exact", "board": SOLUTION, "search_nodes": 1})
        check("unsatisfiable", ["solve", "--puzzle", PUZZLE[:2] + "1" + PUZZLE[3:]], 1,
              {"status": "unsatisfiable", "used_fallback": True})
        for cap in (1, 2):
            check(f"budget-{cap}", ["solve", "--puzzle", PUZZLE, "--node-limit", str(cap)], 1,
                  {"status": "budget_exhausted", "search_nodes": cap, "used_fallback": True})
        for args in (["verify", "--puzzle", PUZZLE], ["solve"], ["unknown"], [],
                     *(["solve", "--puzzle", PUZZLE, "--node-limit", cap] for cap in ("0", "-1", "1.5", "abc"))):
            result = call(prefix, args, 2, json_output=False)
            assert result.stderr and not result.stdout, result
            checks.append(f"{entry}:usage-{len(checks)}")

    probe = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; from concept_firewall.cli import main; "
         f"assert main(['solve','--puzzle','{PUZZLE}']) == 0; "
         f"assert not any(name in sys.modules for name in {forbidden!r})"],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert probe.returncode == 0, probe.stderr
    print(json.dumps({"python": sys.version.split()[0], "version": version,
                      "installed_distributions": installed, "checks_passed": len(checks),
                      "checks": checks, "no_research_dependencies_or_imports": True}, indent=2))


if __name__ == "__main__":
    main()

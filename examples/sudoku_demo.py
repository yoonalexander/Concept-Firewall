"""Run after installing the wheel/sdist: python examples/sudoku_demo.py."""

import json
from pathlib import Path
import subprocess
import sys
import sysconfig


PUZZLE = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"


def main():
    command = Path(sysconfig.get_path("scripts")) / (
        "concept-firewall.exe" if sys.platform == "win32" else "concept-firewall"
    )

    def run(prefix, args, expected):
        process = subprocess.run([*prefix, *args], capture_output=True, text=True, check=False)
        if process.returncode != expected:
            raise RuntimeError(f"exit {process.returncode}, expected {expected}: {process.stderr}")
        return json.loads(process.stdout)

    rejected = run([str(command)], ["verify", "--puzzle", PUZZLE, "--board", "0" * 81], 1)
    solved = run([str(command)], ["solve", "--puzzle", PUZZLE, "--board", "0" * 81], 0)
    verified = run([sys.executable, "-m", "concept_firewall"],
                   ["verify", "--puzzle", PUZZLE, "--board", solved["board"]], 0)
    if rejected["is_valid"] or not solved["verified"] or not verified["is_valid"]:
        raise RuntimeError("Demo result did not meet verifier contract")
    print(json.dumps({"rejected_proposal": rejected, "exact_fallback": solved,
                      "rechecked_completion": verified}, indent=2))


if __name__ == "__main__":
    main()

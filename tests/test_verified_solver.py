import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from concept_firewall.cli import main
from concept_firewall.diagnostics import independent_inspection
from concept_firewall.verified_solver import verified_completion


PUZZLE = '530070000600195000098000060800060003400803001700020006060000280000419005000080079'
SOLUTION = '534678912672195348198342567859761423426853791713924856961537284287419635345286179'


class VerifiedSolverTests(unittest.TestCase):
    def test_preserves_valid_proposal_without_search(self):
        result = verified_completion(PUZZLE, SOLUTION, node_limit=1)
        self.assertEqual(result.status, 'accepted_proposal')
        self.assertEqual(result.board, SOLUTION)
        self.assertEqual(result.search_nodes, 0)
        self.assertFalse(result.used_fallback)

    def test_rejects_bad_proposal_and_solves_original_clues(self):
        for proposal in (None, 'not a board', '0'*81, SOLUTION[1]+SOLUTION[1:]):
            with self.subTest(proposal=proposal):
                result = verified_completion(PUZZLE, proposal)
                self.assertTrue(result.verified)
                self.assertEqual(result.status, 'solved_exact')
                self.assertEqual(result.board, SOLUTION)
                self.assertTrue(independent_inspection(PUZZLE, result.board)['valid'])

    def test_invalid_unsatisfiable_and_budget_exhausted_return_no_board(self):
        for puzzle in ('bad input', '55'+'0'*79):
            self.assertEqual(verified_completion(puzzle).status, 'invalid_puzzle')
        unsatisfiable = PUZZLE[:2]+'1'+PUZZLE[3:]
        self.assertEqual(verified_completion(unsatisfiable).status, 'unsatisfiable')
        limited = verified_completion(PUZZLE, node_limit=1)
        self.assertEqual(limited.status, 'budget_exhausted')
        self.assertIsNone(limited.board)
        self.assertEqual(limited.search_nodes, 1)
        for cap in (False, 0, -1, 1.5):
            with self.assertRaises(ValueError):
                verified_completion(PUZZLE, node_limit=cap)

    def test_digit_renaming_and_transposition(self):
        renamed = PUZZLE.translate(str.maketrans('123456789', '987654321'))
        transposed = ''.join(renamed[column*9+row] for row in range(9) for column in range(9))
        result = verified_completion(transposed)
        self.assertTrue(result.verified)
        self.assertTrue(independent_inspection(transposed, result.board)['valid'])

    def test_cli_and_no_ml_imports(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = main(['solve', '--puzzle', PUZZLE, '--board', '0'*81])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())['board'], SOLUTION)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(['solve', '--puzzle', PUZZLE, '--node-limit', '1']), 1)
        root = Path(__file__).resolve().parents[1]
        script = "import sys; from concept_firewall.verified_solver import verified_completion; verified_completion('0'*81); assert not any(k in sys.modules for k in ('torch','numpy','scipy','sklearn'))"
        process = subprocess.run([sys.executable, '-c', script], env=dict(os.environ, PYTHONPATH=str(root/'src')), capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)

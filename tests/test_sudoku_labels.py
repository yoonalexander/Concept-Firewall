"""Adversarial tests for exact, reference-free Sudoku verification."""

from dataclasses import FrozenInstanceError
import unittest

from concept_firewall.sudoku_labels import (
    SudokuParseError,
    parse_board,
    validate_sudoku,
    verify_sudoku,
)


SOLUTION = (
    "534678912"
    "672195348"
    "198342567"
    "859761423"
    "426853791"
    "713924856"
    "961537284"
    "287419635"
    "345286179"
)
PUZZLE = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)
EMPTY = "0" * 81


class SudokuParsingTests(unittest.TestCase):
    def test_compact_solution(self):
        board = parse_board(SOLUTION)
        self.assertIsInstance(board, tuple)
        self.assertEqual(len(board), 81)
        self.assertEqual(board[:9], (5, 3, 4, 6, 7, 8, 9, 1, 2))

    def test_blank_notations_normalize_to_zero(self):
        self.assertEqual(parse_board(PUZZLE), parse_board(PUZZLE.replace("0", ".")))
        self.assertEqual(parse_board(PUZZLE), parse_board(PUZZLE.replace("0", "_")))

    def test_upstream_89_character_pipe_format(self):
        for board in (SOLUTION, PUZZLE.replace("0", "_")):
            upstream = "|".join(board[index:index + 9] for index in range(0, 81, 9))
            with self.subTest(board=board):
                self.assertEqual(len(upstream), 89)
                self.assertEqual(parse_board(upstream), parse_board(board))
                self.assertEqual(parse_board(" \n".join(upstream)), parse_board(board))

    def test_rejects_misplaced_pipe_separators(self):
        rows = [SOLUTION[index:index + 9] for index in range(0, 81, 9)]
        for text in (
            "|" + "|".join(rows),
            "|".join(rows) + "|",
            "||".join(rows),
            "|".join(rows[:-1]),
            "|".join(rows + [rows[0]]),
            SOLUTION[:8] + "|" + SOLUTION[8:],
            "|".join([rows[0][:-1], rows[0][-1] + rows[1]] + rows[2:]),
        ):
            with self.subTest(text=text), self.assertRaises(SudokuParseError):
                parse_board(text)

    def test_ascii_whitespace_is_explicitly_supported(self):
        spaced = " \n\t" + " \r\n".join(SOLUTION) + "\v\f"
        self.assertEqual(parse_board(spaced), parse_board(SOLUTION))

    def test_complete_parse_rejects_blanks(self):
        for blank in ("0", ".", "_"):
            with self.subTest(blank=blank), self.assertRaises(SudokuParseError):
                parse_board(SOLUTION[:-1] + blank, allow_blanks=False)

    def test_wrong_cell_counts(self):
        for text in ("", " " * 81, SOLUTION[:-1], SOLUTION + "1"):
            with self.subTest(length=len(text)), self.assertRaises(SudokuParseError):
                parse_board(text)

    def test_no_silent_digit_extraction(self):
        for text in (
            "Answer: " + SOLUTION,
            "```\n" + SOLUTION + "\n```",
            ",".join(SOLUTION),
            "|".join(SOLUTION),
            "-" + SOLUTION,
            SOLUTION + "<eos>",
            SOLUTION[:40] + "x" + SOLUTION[41:],
            SOLUTION[:-1] + "\x00",
        ):
            with self.subTest(text=text), self.assertRaises(SudokuParseError):
                parse_board(text)

    def test_unicode_lookalikes_and_hidden_separators(self):
        for char in ("１", "١", "²", "\u200b", "\u00a0", "\ufeff"):
            with self.subTest(char=char), self.assertRaises(SudokuParseError):
                parse_board(SOLUTION[:-1] + char)

    def test_non_string_input(self):
        for value in (None, list(SOLUTION), 123, True, SOLUTION.encode("ascii")):
            with self.subTest(value=type(value).__name__), self.assertRaises(SudokuParseError):
                parse_board(value)


class SudokuValidationTests(unittest.TestCase):
    def test_valid_solution_and_diagnostics(self):
        result = validate_sudoku(PUZZLE, SOLUTION)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.is_complete)
        self.assertFalse(result.malformed)
        self.assertEqual(result.filled_cells, 81)
        self.assertEqual(result.blank_cells, 0)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.clue_violations, 0)
        self.assertEqual(result.row_conflicts + result.column_conflicts + result.box_conflicts, 0)

    def test_upstream_puzzle_and_prediction_verify(self):
        puzzle = "|".join(PUZZLE[index:index + 9] for index in range(0, 81, 9)).replace("0", "_")
        output = "|".join(SOLUTION[index:index + 9] for index in range(0, 81, 9))
        self.assertTrue(verify_sudoku(puzzle, output))

    def test_upstream_blank_prediction_is_incomplete(self):
        output = "|".join(PUZZLE[index:index + 9] for index in range(0, 81, 9)).replace("0", "_")
        result = validate_sudoku(PUZZLE, output)
        self.assertFalse(result.is_valid)
        self.assertFalse(result.malformed)
        self.assertEqual(result.filled_cells, 30)
        self.assertEqual(result.clue_violations, 0)
        self.assertEqual(result.errors, ("incomplete_output",))

    def test_accepts_all_valid_digit_relabelings(self):
        # This checks all 9 cyclic digit mappings, without relying on a solver.
        for offset in range(9):
            mapping = str.maketrans("123456789", "123456789"[offset:] + "123456789"[:offset])
            with self.subTest(offset=offset):
                self.assertTrue(verify_sudoku(PUZZLE.translate(mapping), SOLUTION.translate(mapping)))

    def test_alternative_valid_completions_preserving_clues(self):
        puzzle = "".join("0" if char in "12" else char for char in SOLUTION)
        alternative = SOLUTION.translate(str.maketrans("12", "21"))
        self.assertNotEqual(alternative, SOLUTION)
        self.assertTrue(verify_sudoku(puzzle, SOLUTION))
        self.assertTrue(verify_sudoku(puzzle, alternative))

    def test_complete_output_can_still_change_clues(self):
        alternative = SOLUTION.translate(str.maketrans("12", "21"))
        result = validate_sudoku(PUZZLE, alternative)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.is_complete)
        self.assertGreater(result.clue_violations, 0)
        self.assertEqual(result.row_conflicts + result.column_conflicts + result.box_conflicts, 0)
        self.assertIn("changed_clues", result.errors)

    def test_incomplete_board_fails_even_without_conflicts(self):
        for blank in ("0", ".", "_"):
            result = validate_sudoku(EMPTY, SOLUTION[:-1] + blank)
            with self.subTest(blank=blank):
                self.assertFalse(result.is_valid)
                self.assertFalse(result.is_complete)
                self.assertFalse(result.malformed)
                self.assertEqual(result.filled_cells, 80)
                self.assertEqual(result.blank_cells, 1)
                self.assertEqual(result.errors, ("incomplete_output",))

    def test_missing_clue_is_a_clue_violation(self):
        result = validate_sudoku(PUZZLE, "0" + SOLUTION[1:])
        self.assertEqual(result.clue_violations, 1)
        self.assertIn("changed_clues", result.errors)

    def test_empty_board_is_incomplete_not_malformed(self):
        result = validate_sudoku(EMPTY, "." * 81)
        self.assertFalse(result.is_valid)
        self.assertFalse(result.malformed)
        self.assertEqual(result.filled_cells, 0)
        self.assertEqual(result.row_conflicts + result.column_conflicts + result.box_conflicts, 0)

    def test_repeated_digits_rejected_with_defined_counts(self):
        result = validate_sudoku(EMPTY, "1" * 81)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.row_conflicts, 72)
        self.assertEqual(result.column_conflicts, 72)
        self.assertEqual(result.box_conflicts, 72)

    def test_duplicate_in_each_single_constraint_type(self):
        cases = ((0, 3, "row"), (0, 27, "column"), (0, 10, "box"))
        for first, second, kind in cases:
            values = ["0"] * 81
            values[first] = values[second] = "1"
            result = validate_sudoku(EMPTY, "".join(values))
            with self.subTest(kind=kind):
                self.assertEqual(result.row_conflicts, int(kind == "row"))
                self.assertEqual(result.column_conflicts, int(kind == "column"))
                self.assertEqual(result.box_conflicts, int(kind == "box"))

    def test_latin_square_rows_columns_do_not_imply_valid_boxes(self):
        latin = "".join(str((row + col) % 9 + 1) for row in range(9) for col in range(9))
        result = validate_sudoku(EMPTY, latin)
        self.assertTrue(result.is_complete)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.row_conflicts, 0)
        self.assertEqual(result.column_conflicts, 0)
        self.assertGreater(result.box_conflicts, 0)
        self.assertEqual(result.errors, ("box_conflicts",))

    def test_malformed_output_fails_closed(self):
        for output in (None, SOLUTION[:-1], SOLUTION + "9", "Answer " + SOLUTION):
            result = validate_sudoku(PUZZLE, output)
            with self.subTest(output=output):
                self.assertFalse(result.is_valid)
                self.assertTrue(result.malformed)
                self.assertFalse(result.is_complete)
                self.assertIsNone(result.board)
                self.assertTrue(any(error.startswith("malformed_output:") for error in result.errors))

    def test_malformed_puzzle_fails_closed(self):
        result = validate_sudoku(PUZZLE[:-1], SOLUTION)
        self.assertFalse(result.is_valid)
        self.assertFalse(result.malformed)
        self.assertTrue(result.is_complete)
        self.assertTrue(result.errors[0].startswith("invalid_puzzle:"))

    def test_contradictory_puzzle_clues_fail_closed(self):
        for first, second in ((0, 3), (0, 27), (0, 10)):
            values = ["0"] * 81
            values[first] = values[second] = "1"
            result = validate_sudoku("".join(values), SOLUTION)
            with self.subTest(second=second):
                self.assertFalse(result.is_valid)
                self.assertIn("invalid_puzzle: contradictory clues", result.errors)

    def test_validation_result_is_immutable(self):
        result = validate_sudoku(PUZZLE, SOLUTION)
        with self.assertRaises(FrozenInstanceError):
            result.is_valid = False
        with self.assertRaises(TypeError):
            result.board[0] = 0


if __name__ == "__main__":
    unittest.main()

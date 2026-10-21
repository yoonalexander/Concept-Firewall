"""Exact Sudoku labels and reference-free diagnostics.

The text format is 81 ASCII cell characters, optionally separated by ASCII
whitespace or arranged as nine rows separated by ``|`` as upstream emits.
Digits 1-9 are filled cells; ``0``, ``.``, and upstream's ``_`` represent blanks.
Labels never depend on a stored solution or on puzzle uniqueness. Formatting
such as prose, Markdown fences, comma-separated values, or other grid borders must be
handled explicitly by the caller rather than silently discarded here.
"""

from __future__ import annotations

from dataclasses import dataclass


Board = tuple[int, ...]
_WHITESPACE = frozenset(" \t\r\n\v\f")
_ROW_UNITS = tuple(tuple(row * 9 + col for col in range(9)) for row in range(9))
_COLUMN_UNITS = tuple(tuple(row * 9 + col for row in range(9)) for col in range(9))
_BOX_UNITS = tuple(
    tuple((box_row + row) * 9 + box_col + col for row in range(3) for col in range(3))
    for box_row in (0, 3, 6)
    for box_col in (0, 3, 6)
)


class SudokuParseError(ValueError):
    """The input does not conform to the explicit 81-cell text format."""


@dataclass(frozen=True)
class SudokuValidation:
    """A correctness label with inexpensive diagnostics of the decoded board.

    Conflict counts are duplicate occurrences beyond the first within each
    unit, summed over the nine units of that type. Blanks never cause conflicts.
    ``malformed`` concerns the output; invalid puzzle input is recorded in
    ``errors``. An incomplete output is parseable but never correct.
    """

    is_valid: bool
    is_complete: bool
    malformed: bool
    filled_cells: int
    clue_violations: int
    row_conflicts: int
    column_conflicts: int
    box_conflicts: int
    errors: tuple[str, ...]
    board: Board | None

    @property
    def blank_cells(self) -> int:
        """Number of blanks, or 81 when the output cannot be parsed."""
        return 81 - self.filled_cells


def parse_board(text: str, *, allow_blanks: bool = True) -> Board:
    """Parse exactly 81 cells without extracting digits from malformed text.

    ASCII whitespace may occur anywhere. If ``|`` occurs, exactly nine rows of
    nine cells must be present. Other characters, including Unicode lookalike
    digits and whitespace, are rejected. Set ``allow_blanks=False``
    when a complete board is required at the parsing boundary.
    """
    if not isinstance(text, str):
        raise SudokuParseError("board must be a string")
    cell_characters: list[str] = []
    for position, char in enumerate(text):
        if char in _WHITESPACE:
            continue
        if char not in "123456789|" and not (char in "0._" and allow_blanks):
            raise SudokuParseError(f"invalid cell character {char!r} at text position {position}")
        cell_characters.append(char)
    normalized = "".join(cell_characters)
    if "|" in normalized:
        rows = normalized.split("|")
        if len(rows) != 9 or any(len(row) != 9 for row in rows):
            raise SudokuParseError("pipe-delimited board must contain exactly nine rows of nine cells")
        normalized = "".join(rows)
    cells = tuple(int(char) if char in "123456789" else 0 for char in normalized)
    if len(cells) != 81:
        raise SudokuParseError(f"expected exactly 81 cells, found {len(cells)}")
    return cells


def _conflicts(board: Board, units: tuple[tuple[int, ...], ...]) -> int:
    total = 0
    for unit in units:
        values = [board[index] for index in unit if board[index] != 0]
        total += len(values) - len(set(values))
    return total


def validate_sudoku(puzzle: str, output: str) -> SudokuValidation:
    """Validate an output against puzzle clues and every Sudoku constraint.

    Both malformed output and malformed or contradictory puzzle input fail
    closed. This checks consistency of supplied clues, not existence/uniqueness
    of a solution. No solver, reference completion, or probabilistic rule is
    used. Diagnostics remain available for parseable intermediate boards.
    """
    errors: list[str] = []
    clues: Board | None = None
    board: Board | None = None
    try:
        clues = parse_board(puzzle)
    except SudokuParseError as exc:
        errors.append(f"invalid_puzzle: {exc}")
    if clues is not None:
        if any(_conflicts(clues, units) for units in (_ROW_UNITS, _COLUMN_UNITS, _BOX_UNITS)):
            errors.append("invalid_puzzle: contradictory clues")
    try:
        board = parse_board(output)
    except SudokuParseError as exc:
        errors.append(f"malformed_output: {exc}")

    filled_cells = sum(value != 0 for value in board) if board is not None else 0
    complete = board is not None and filled_cells == 81
    clue_violations = (
        sum(clue != 0 and clue != value for clue, value in zip(clues, board))
        if clues is not None and board is not None
        else 0
    )
    row_conflicts = _conflicts(board, _ROW_UNITS) if board is not None else 0
    column_conflicts = _conflicts(board, _COLUMN_UNITS) if board is not None else 0
    box_conflicts = _conflicts(board, _BOX_UNITS) if board is not None else 0
    if board is not None and not complete:
        errors.append("incomplete_output")
    if clue_violations:
        errors.append("changed_clues")
    if row_conflicts:
        errors.append("row_conflicts")
    if column_conflicts:
        errors.append("column_conflicts")
    if box_conflicts:
        errors.append("box_conflicts")
    return SudokuValidation(
        is_valid=not errors,
        is_complete=complete,
        malformed=board is None,
        filled_cells=filled_cells,
        clue_violations=clue_violations,
        row_conflicts=row_conflicts,
        column_conflicts=column_conflicts,
        box_conflicts=box_conflicts,
        errors=tuple(errors),
        board=board,
    )


def verify_sudoku(puzzle: str, output: str) -> bool:
    """Return true exactly when ``output`` is a valid completion of ``puzzle``."""
    return validate_sudoku(puzzle, output).is_valid

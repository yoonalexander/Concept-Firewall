"""Practical Sudoku fallback using exact constraints, without ML dependencies.

This is an engineering baseline, not learned early warning or NCM recovery.
"""
from __future__ import annotations

from dataclasses import dataclass

from .sudoku_labels import SudokuParseError, parse_board, validate_sudoku


@dataclass(frozen=True)
class VerifiedCompletion:
    status: str
    board: str | None
    verified: bool
    used_fallback: bool
    search_nodes: int
    reason: str


def verified_completion(puzzle: str, proposed_board: str | None = None, *, node_limit: int = 100000) -> VerifiedCompletion:
    """Keep a valid proposal, otherwise solve only from the original clues.

    Minimum-remaining-values backtracking is deterministic. Budget exhaustion,
    inconsistent input and unsatisfiability return no answer, never an unchecked
    partial grid. Nonunique puzzles may return any valid completion.
    """
    if type(node_limit) is not int or node_limit < 1:
        raise ValueError('node_limit must be a positive integer')
    try:
        cells = list(parse_board(puzzle))
    except SudokuParseError as error:
        return VerifiedCompletion('invalid_puzzle', None, False, False, 0, str(error))
    rows, columns, boxes = [0]*9, [0]*9, [0]*9
    for at, value in enumerate(cells):
        if not value:
            continue
        row, column = divmod(at, 9)
        box, bit = row//3*3+column//3, 1 << (value-1)
        if (rows[row] | columns[column] | boxes[box]) & bit:
            return VerifiedCompletion('invalid_puzzle', None, False, False, 0, 'Original clues conflict')
        rows[row] |= bit
        columns[column] |= bit
        boxes[box] |= bit
    if proposed_board is not None:
        proposed = validate_sudoku(puzzle, proposed_board)
        if proposed.is_valid:
            return VerifiedCompletion('accepted_proposal', ''.join(map(str, proposed.board)), True, False, 0, 'Exact verifier accepted original answer')
    nodes, exhausted = 0, False

    def search():
        nonlocal nodes, exhausted
        if nodes >= node_limit:
            exhausted = True
            return False
        nodes += 1
        best, choices, smallest = -1, 0, 10
        for at, value in enumerate(cells):
            if value:
                continue
            row, column = divmod(at, 9)
            box = row//3*3+column//3
            available = 511 & ~(rows[row] | columns[column] | boxes[box])
            size = available.bit_count()
            if size == 0:
                return False
            if size < smallest:
                best, choices, smallest = at, available, size
                if size == 1:
                    break
        if best < 0:
            return True
        row, column = divmod(best, 9)
        box = row//3*3+column//3
        while choices and not exhausted:
            bit = choices & -choices
            choices ^= bit
            cells[best] = bit.bit_length()
            rows[row] |= bit
            columns[column] |= bit
            boxes[box] |= bit
            if search():
                return True
            rows[row] ^= bit
            columns[column] ^= bit
            boxes[box] ^= bit
            cells[best] = 0
        return False

    if search():
        board = ''.join(map(str, cells))
        if not validate_sudoku(puzzle, board).is_valid:
            raise RuntimeError('Exact solver returned an invalid completion')
        return VerifiedCompletion('solved_exact', board, True, True, nodes, 'Solved from original clues and independently rechecked by verifier')
    status = 'budget_exhausted' if exhausted else 'unsatisfiable'
    return VerifiedCompletion(status, None, False, True, nodes,
                              'No unchecked answer returned after node limit' if exhausted else 'No completion satisfies all original clues')

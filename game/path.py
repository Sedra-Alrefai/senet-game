from __future__ import annotations
from dataclasses import dataclass
from .constants import BOARD_COLS, BOARD_ROWS, NUM_SQUARES

@dataclass(frozen=True)
class Cell:
    row: int
    col: int

def index_to_cell(square: int) -> Cell:
    """
    square in 1..30
    row 0 is top, row 2 is bottom
    snake pattern:
        row0: 1..10 left->right
        row1: 20..11 right->left
        row2: 21..30 left->right
    """
    if not (1 <= square <= NUM_SQUARES):
        raise ValueError("square must be in 1..30")

    # Determine row
    if 1 <= square <= 10:
        row = 0
        col = square - 1
    elif 11 <= square <= 20:
        row = 1
        # row1 is reversed: 20 at col0, 11 at col9
        col = 20 - square
    else:  # 21..30
        row = 2
        col = square - 21

    return Cell(row=row, col=col)

def cell_to_index(row: int, col: int) -> int | None:
    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return None

    if row == 0:
        return col + 1
    if row == 1:
        return 20 - col
    # row == 2
    return 21 + col

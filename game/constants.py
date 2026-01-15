from __future__ import annotations

BOARD_COLS = 10
BOARD_ROWS = 3
NUM_SQUARES = BOARD_COLS * BOARD_ROWS  # 30

PIECES_PER_PLAYER = 7

REBIRTH = 15
HAPPINESS = 26
WATER = 27
THREE_TRUTHS = 28
RE_ATOUM = 29
HORUS = 30

LAST_FIVE = {HAPPINESS, WATER, THREE_TRUTHS, RE_ATOUM, HORUS}

# Stick toss distribution (as per your rule: sum=0 -> move 5)
# 4 sticks, each 0/1 => sum in {0..4}, where 0 becomes 5.
# Probabilities:
# 0 -> 5: 1/16
# 1: 4/16
# 2: 6/16
# 3: 4/16
# 4: 1/16
ROLL_PROBS = {
    1: 4 / 16,
    2: 6 / 16,
    3: 4 / 16,
    4: 1 / 16,
    5: 1 / 16,
}

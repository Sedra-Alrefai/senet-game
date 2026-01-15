from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional, Tuple

class Player(str, Enum):
    BLACK = "BLACK"
    WHITE = "WHITE"

OUT = 0  # position 0 means the piece is out (promoted)

# pending rule: (player, piece_id, required_roll)
# required_roll can be 2,3 or None meaning ANY (for Horus)
Pending = Optional[Tuple[Player, int, Optional[int]]]

@dataclass(frozen=True)
class GameState:
    black: tuple[int, ...]   # length 7, each in {0..30}
    white: tuple[int, ...]   # length 7
    turn: Player
    pending: Pending = None

    def swap_turn(self) -> "GameState":
        nxt = Player.WHITE if self.turn == Player.BLACK else Player.BLACK
        return replace(self, turn=nxt)

    def pieces_of(self, p: Player) -> tuple[int, ...]:
        return self.black if p == Player.BLACK else self.white

    def set_pieces_of(self, p: Player, new_positions: tuple[int, ...]) -> "GameState":
        if p == Player.BLACK:
            return replace(self, black=new_positions)
        return replace(self, white=new_positions)

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class MoveKind(str, Enum):
    MOVE = "MOVE"
    PROMOTE = "PROMOTE"  # move to OUT (exit square)

@dataclass(frozen=True)
class Move:
    piece_id: int  # 0..6
    kind: MoveKind = MoveKind.MOVE

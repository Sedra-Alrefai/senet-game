from __future__ import annotations
import random
from .constants import ROLL_PROBS

def toss_sticks(rng: random.Random | None = None) -> int:
    """
    4 sticks each gives 0/1. sum=0 => treated as 5.
    Returns in {1,2,3,4,5}.
    """
    rng = rng or random
    s = sum(rng.choice([0, 1]) for _ in range(4))
    return 5 if s == 0 else s

def roll_distribution() -> dict[int, float]:
    return dict(ROLL_PROBS)

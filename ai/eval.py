from __future__ import annotations
from game.state import GameState, Player, OUT
from game.constants import HAPPINESS, WATER, HORUS, THREE_TRUTHS, RE_ATOUM, REBIRTH
from game.rules import _occupied_map

WEIGHT_PROMOTED = 200000000.0     
WEIGHT_HAPPINESS_STAY = 50000000.0
WEIGHT_HORUS_STAY = 80000000.0     

WEIGHT_OP_ON_HAPPINESS = -300000000.0 
WEIGHT_DANGER_ZONE = -100000000.0  
WEIGHT_TRAFFIC_JAM = -20000000.0

WEIGHT_BLOCKING_OP = 15000000.0
WEIGHT_ADVANCED_POSITION = 3000000.0
WEIGHT_REBIRTH_PENALTY = -50000000.0
WEIGHT_OP_REBIRTH_BONUS = 20000000.0
WEIGHT_NEAR_PROMOTION = 40000000.0
WEIGHT_OP_BLOCKED = 10000000.0

def evaluate(state: GameState, ai_player: Player) -> float:
    my_pieces = state.pieces_of(ai_player)
    opponent = Player.WHITE if ai_player == Player.BLACK else Player.BLACK
    op_pieces = state.pieces_of(opponent)
    occ = _occupied_map(state)

    score = 0.0

    my_out = sum(1 for p in my_pieces if p == OUT)
    op_out = sum(1 for p in op_pieces if p == OUT)
    score += my_out * WEIGHT_PROMOTED
    score += op_out * -50000000.0

    if any(p == HAPPINESS for p in op_pieces):
        score += WEIGHT_OP_ON_HAPPINESS 

    my_on_happiness = False
    waiting_behind_happiness = 0
    my_advanced_count = 0
    op_blocked_count = 0
    for p in my_pieces:
        if p == OUT: continue

        if p == HAPPINESS:
            my_on_happiness = True
            score += WEIGHT_HAPPINESS_STAY
        
        elif p == HORUS:
            score += WEIGHT_HORUS_STAY

        elif p == WATER or p in (27, 28, 29):
            score += WEIGHT_DANGER_ZONE

        elif p in (THREE_TRUTHS, RE_ATOUM):
            score += WEIGHT_NEAR_PROMOTION

        elif p == REBIRTH:
            score += WEIGHT_REBIRTH_PENALTY

        else:
            if p >= 20: 
                score += p * 50000
                my_advanced_count += 1
                if p < 26: 
                    waiting_behind_happiness += 1
                if p >= 23:
                    score += WEIGHT_ADVANCED_POSITION
            else: 
                score += p * 1000

    for p in op_pieces:
        if p == OUT: continue

        if p == HAPPINESS:
            score += WEIGHT_OP_ON_HAPPINESS

        elif p == REBIRTH:
            score += WEIGHT_OP_REBIRTH_BONUS

        elif p in (THREE_TRUTHS, RE_ATOUM, HORUS):
            score -= 40000000.0

        elif p >= 20:
            score -= p * 40000
            if p < 26:
                for my_pos in my_pieces:
                    if my_pos != OUT and my_pos > p and my_pos <= 26:
                        op_blocked_count += 1
                        score += WEIGHT_OP_BLOCKED
                        break

    if op_blocked_count > 0:
        score += op_blocked_count * WEIGHT_BLOCKING_OP

    if my_on_happiness and waiting_behind_happiness > 0:
        score += (waiting_behind_happiness * WEIGHT_TRAFFIC_JAM)

    op_advanced = sum(1 for p in op_pieces if p != OUT and p >= 20)
    if my_advanced_count > op_advanced:
        score += (my_advanced_count - op_advanced) * 5000000.0

    return score
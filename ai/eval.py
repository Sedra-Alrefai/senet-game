from __future__ import annotations
from game.state import GameState, Player, OUT
from game.constants import HAPPINESS, WATER, HORUS

WEIGHT_PROMOTED = 100000.0
WEIGHT_OP_PROMOTED = -15000.0
WEIGHT_REBIRTH_BONUS = 2000.0

def evaluate(state: GameState, ai_player: Player) -> float:
    my_pieces = state.pieces_of(ai_player)
    opponent = Player.WHITE if ai_player == Player.BLACK else Player.BLACK
    op_pieces = state.pieces_of(opponent)
    
    def get_performance_metrics(pieces):
        total_steps = 0
        out_count = 0
        advanced_count = 0
        for p in pieces:
            if p == OUT:
                out_count += 1
            else:
                total_steps += (31 - p)
                if p >= 20: advanced_count += 1
        return total_steps, out_count, advanced_count

    my_steps, my_out, my_adv = get_performance_metrics(my_pieces)
    op_steps, op_out, op_adv = get_performance_metrics(op_pieces)

    
    gap = (op_steps * 1.5) - (my_steps * 1.0)
    
   
    gap += (my_out * WEIGHT_PROMOTED)
    gap += (op_out * WEIGHT_OP_PROMOTED)

    
    for p in my_pieces:
        if p == WATER: gap -= 5000
        if p == HAPPINESS: gap += 2500
        if p == HORUS: gap += 4000

    
    for p in op_pieces:
        if p != OUT and p >= 25:
            gap -= (p - 20) * 500

   
    if op_out == 0 and my_out < 2:
        my_positions = sorted([p for p in my_pieces if p != OUT])
        for i in range(len(my_positions) - 1):
            if my_positions[i+1] - my_positions[i] == 1:
                gap += 10
    
    return gap
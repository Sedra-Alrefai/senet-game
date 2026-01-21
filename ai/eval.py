from __future__ import annotations
from game.state import GameState, Player, OUT
from game.constants import HAPPINESS, WATER, HORUS, THREE_TRUTHS, RE_ATOUM, REBIRTH
from game.rules import _occupied_map

W_WIN = 20000000.0        
W_KILL = 50000.0           
W_VANGUARD = 4000.0        
W_BLOCKING = 3000.0       
W_BRIDGE = 1500.0          
W_SAFETY = 2000.0          
W_DANGER_OP = -10000.0     

def evaluate(state: GameState, ai_player: Player) -> float:
    my_pieces = sorted([p for p in state.pieces_of(ai_player) if p != OUT])
    opponent = Player.WHITE if ai_player == Player.BLACK else Player.BLACK
    op_pieces = sorted([p for p in state.pieces_of(opponent) if p != OUT])
    
    score = 0.0
    my_out_count = 7 - len(my_pieces)
    op_out_count = 7 - len(op_pieces)
    score += (my_out_count * W_WIN)
    score -= (op_out_count * W_WIN * 1.5) 
    vanguard_count = min(3, len(my_pieces))
    vanguard_pieces = my_pieces[-vanguard_count:] if vanguard_count > 0 else []

    for p in my_pieces:
        if p == 27: score -= 5000000.0 
        
        if p in vanguard_pieces:
            score += (p * W_VANGUARD) 
            if p >= 26: score += 50000.0
        else:
            score += (p * 10.0)

    op_threat_level = 0
    for op in op_pieces:
        if op >= 24 and op <= 26:
            op_threat_level += op
            score -= (op * 5000.0) 

    for i in range(len(my_pieces) - 1):
        if my_pieces[i] + 1 == my_pieces[i+1]:
            if my_pieces[i] < 22:
                score += W_BRIDGE
            else:
                score -= 1000.0 
    op_total_progress = sum(p for p in op_pieces)
    score -= (op_total_progress * 200.0)

    return score
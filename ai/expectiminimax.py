
from __future__ import annotations
from dataclasses import dataclass
from math import inf
from typing import Optional, Tuple
from game.state import GameState, Player, OUT
from game.rules import legal_moves, apply_move, skip_turn, is_terminal
from game.dice import roll_distribution
from game.move import Move
from game.constants import HAPPINESS, THREE_TRUTHS, RE_ATOUM, HORUS
from .eval import evaluate

@dataclass
class SearchStats:
    nodes: int = 0
    leafs: int = 0

PRINT_TREE = False 

def filter_suicide_moves(state: GameState, moves: list[Move], roll: int) -> list[Move]:

    if roll in (4, 5):
        return moves
    
    my_pieces = state.pieces_of(state.turn)
    suicide_moves = []
    safe_moves = []
    
    for mv in moves:
        piece_pos = my_pieces[mv.piece_id]
        if piece_pos == HAPPINESS:
            suicide_moves.append(mv)
        else:
            safe_moves.append(mv)
    if safe_moves:
        return safe_moves
    
    return suicide_moves

def _order_moves(moves: list[Move], state: GameState, roll: int, ai_player: Player) -> list[Move]:
    opp = Player.WHITE if state.turn == Player.BLACK else Player.BLACK
    op_pieces = state.pieces_of(opp)
    my_pieces = state.pieces_of(state.turn)

    def move_priority(mv):
        piece_pos = my_pieces[mv.piece_id]
        target_pos = piece_pos + roll
        if piece_pos == 27: 
            return 100_000_000 
        if mv.kind == MoveKind.PROMOTE:
            return 50_000_000 
        if target_pos in op_pieces:
            return 1_000_000 + (target_pos * 10_000)
        if target_pos == 26: 
            return 500_000
        if piece_pos > 20:
            return piece_pos * 1000 
        return target_pos 
    return sorted(moves, key=move_priority, reverse=True)

def choose_best_move_given_roll(state: GameState, ai_player: Player, depth: int, roll: int) -> tuple[object, float, SearchStats]:
    stats = SearchStats()
    dist = roll_distribution()
    def value_turn(s: GameState, d: int) -> float:
        stats.nodes += 1
        if d == 0 or is_terminal(s):
            stats.leafs += 1
            return evaluate(s, ai_player)
        
        exp_val = 0.0
        for r, p in dist.items():
            v, _ = value_after_roll(s, d, r, -inf, inf)
            exp_val += p * v
        return exp_val
    def value_after_roll(s: GameState, d: int, r: int, alpha: float, beta: float) -> Tuple[float, Optional[Move]]:
        raw_moves = legal_moves(s, r)
        moves = filter_suicide_moves(s, raw_moves, r) if s.turn == ai_player else raw_moves

        if not moves:
            return value_turn(skip_turn(s, r), d - 1), None

        maximizing = (s.turn == ai_player)
        best_val = -inf if maximizing else inf
        best_move = None
        if d >= 1: 
            moves = _order_moves(moves, s, r, ai_player)

        for mv in moves:
            s2 = apply_move(s, r, mv)
            val = value_turn(s2, d - 1)
            
            if maximizing:
                if val > best_val:
                    best_val = val
                    best_move = mv
                alpha = max(alpha, best_val)
            else:
                if val < best_val:
                    best_val = val
                    best_move = mv
                beta = min(beta, best_val)
            if beta <= alpha:
                break 

        return best_val, best_move
    raw_moves = legal_moves(state, roll)
    moves = filter_suicide_moves(state, raw_moves, roll) if state.turn == ai_player else raw_moves

    if not moves:
        val = value_turn(skip_turn(state, roll), depth - 1)
        return None, val, stats
    moves = _order_moves(moves, state, roll, ai_player)
    
    best_mv = None
    best_val = -inf
    alpha = -inf
    
    for mv in moves:
        s2 = apply_move(state, roll, mv)
        v = value_turn(s2, depth - 1)
        
        if v > best_val:
            best_val = v
            best_mv = mv
        
        alpha = max(alpha, best_val)

    return best_mv, best_val, stats
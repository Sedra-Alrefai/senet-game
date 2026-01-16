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
    if not moves: return moves
    from game.move import MoveKind
    from game.rules import _occupied_map
    from math import inf
    
    high_priority_promote = []
    normal_promote = []
    other_moves = []
    
    my_pieces = state.pieces_of(state.turn)
    occ = _occupied_map(state)
    
    for mv in moves:
        if mv.kind == MoveKind.PROMOTE:
            piece_pos = my_pieces[mv.piece_id]
            if piece_pos == HAPPINESS and roll == 5:
                high_priority_promote.append(mv)
            else:
                normal_promote.append(mv)
        else:
            other_moves.append(mv)
    
    move_scores = []
    maximizing = (state.turn == ai_player)
    
    for mv in other_moves:
        try:
            s2 = apply_move(state, roll, mv)
            score = evaluate(s2, ai_player)
            
            piece_pos = my_pieces[mv.piece_id]
            to_pos = piece_pos + roll
            
            if to_pos in occ and occ[to_pos][0] != state.turn and to_pos <= HAPPINESS:
                score += 20000000.0 if maximizing else -20000000.0
            
            if to_pos >= 20 and to_pos < 26:
                for op_pos in state.pieces_of(Player.WHITE if state.turn == Player.BLACK else Player.BLACK):
                    if op_pos != OUT and op_pos < to_pos and op_pos >= 20:
                        score += 10000000.0 if maximizing else -10000000.0
                        break
            
            move_scores.append((score, mv))
        except:
            move_scores.append((-inf if maximizing else inf, mv))
    
    move_scores.sort(reverse=maximizing, key=lambda x: x[0])
    ordered_other = [mv for _, mv in move_scores]
    
    return high_priority_promote + normal_promote + ordered_other

def choose_best_move_given_roll(state: GameState, ai_player: Player, depth: int, roll: int) -> tuple[object, float, SearchStats]:
    stats = SearchStats()
    dist = roll_distribution()

    def value_turn(s: GameState, d: int, alpha: float, beta: float) -> Tuple[float, Optional[Move]]:
        stats.nodes += 1
        if d == 0 or is_terminal(s):
            stats.leafs += 1
            return evaluate(s, ai_player), None
        exp_val = 0.0
        for r, p in dist.items():
            v, _ = value_after_roll(s, d, r, alpha, beta)
            exp_val += p * v
        return exp_val, None

    def value_after_roll(s: GameState, d: int, r: int, alpha: float, beta: float) -> Tuple[float, Optional[Move]]:
        raw_moves = legal_moves(s, r)
        moves = filter_suicide_moves(s, raw_moves, r) if s.turn == ai_player else raw_moves

        if not moves:
            return value_turn(skip_turn(s, r), d - 1, alpha, beta)

        maximizing = (s.turn == ai_player)
        best = -inf if maximizing else inf
        best_move = None
        if d >= 1: moves = _order_moves(moves, s, r, ai_player)

        for mv in moves:
            s2 = apply_move(s, r, mv)
            v, _ = value_turn(s2, d - 1, alpha, beta)
            if maximizing:
                if v > best: best, best_move = v, mv
                alpha = max(alpha, best)
            else:
                if v < best: best, best_move = v, mv
                beta = min(beta, best)
            if beta <= alpha: break
        return best, best_move

    raw_moves = legal_moves(state, roll)
    moves = filter_suicide_moves(state, raw_moves, roll) if state.turn == ai_player else raw_moves

    if not moves:
        val, _ = value_turn(skip_turn(state, roll), depth - 1, -inf, inf)
        return None, val, stats

    moves = _order_moves(moves, state, roll, ai_player)
    
    best_mv, best_val = None, -inf
    alpha, beta = -inf, inf
    
    for mv in moves:
        s2 = apply_move(state, roll, mv)
        v, _ = value_turn(s2, depth - 1, alpha, beta)
        if v > best_val: 
            best_val, best_mv = v, mv
        alpha = max(alpha, best_val)
        if best_val >= beta:
            break
    
    return best_mv, best_val, stats
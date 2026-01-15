from __future__ import annotations
from dataclasses import dataclass
from math import inf
from typing import Optional, Tuple
from game.state import GameState, Player
from game.rules import legal_moves, apply_move, skip_turn, is_terminal
from game.dice import roll_distribution
from game.move import Move
from .eval import evaluate

@dataclass
class SearchStats:
    nodes: int = 0
    leafs: int = 0
PRINT_TREE = True

def _print_node(node_type: str, depth: int, value: float, move: Optional[Move] = None, roll: Optional[int] = None, prob: Optional[float] = None):
    if not PRINT_TREE:
        return
    
    indent = "--" * depth
    move_str = f" | Move: {move}" if move else ""
    roll_str = f" | Roll: {roll}" if roll is not None else ""
    prob_str = f" | Prob: {prob:.3f}" if prob is not None else ""
    print(f"{indent}[{node_type}] Depth: {depth} | Value: {value:.2f}{move_str}{roll_str}{prob_str}")

def choose_best_move(state: GameState, ai_player: Player, depth: int) -> tuple[object, float, SearchStats]:
    stats = SearchStats()
    dist = roll_distribution()

    def value_turn(s: GameState, d: int) -> Tuple[float, Optional[Move]]:
        stats.nodes += 1
        if d == 0 or is_terminal(s):
            stats.leafs += 1
            val = evaluate(s, ai_player)
            _print_node("LEAF", d, val)
            return val, None

        exp_val = 0.0
        for roll, prob in dist.items():
            v, _ = value_after_roll(s, d, roll)
            exp_val += prob * v
            _print_node("CHANCE", d, v, roll=roll, prob=prob)
        
        _print_node("CHANCE", d, exp_val)
        return exp_val, None

    def value_after_roll(s: GameState, d: int, roll: int) -> Tuple[float, Optional[Move]]:
        moves = legal_moves(s, roll)
        if not moves:
            s2 = skip_turn(s, roll)
            return value_turn(s2, d - 1)

        maximizing = (s.turn == ai_player)
        node_type = "MAX" if maximizing else "MIN"
        
        best = -inf if maximizing else inf
        best_move = None

        for mv in moves:
            s2 = apply_move(s, roll, mv)
            v, _ = value_turn(s2, d - 1)
            if maximizing:
                if v > best:
                    best = v
                    best_move = mv
            else:
                if v < best:
                    best = v
                    best_move = mv
        
        _print_node(node_type, d, best, move=best_move, roll=roll)
        return best, best_move

    root_val, _ = value_turn(state, depth)
    return None, root_val, stats

def choose_best_move_given_roll(state: GameState, ai_player: Player, depth: int, roll: int) -> tuple[object, float, SearchStats]:
    stats = SearchStats()
    dist = roll_distribution()

    def value_turn(s: GameState, d: int, alpha: float = -inf, beta: float = inf) -> Tuple[float, Optional[Move]]:
        stats.nodes += 1
        if d == 0 or is_terminal(s):
            stats.leafs += 1
            val = evaluate(s, ai_player)
            _print_node("LEAF", d, val)
            return val, None

        exp_val = 0.0
        for r, p in dist.items():
            v, _ = value_after_roll(s, d, r, alpha, beta)
            exp_val += p * v
            _print_node("CHANCE", d, v, roll=r, prob=p)
        
        _print_node("CHANCE", d, exp_val)
        return exp_val, None

    def value_after_roll(s: GameState, d: int, r: int, alpha: float = -inf, beta: float = inf) -> Tuple[float, Optional[Move]]:
        moves = legal_moves(s, r)
        if not moves:
            return value_turn(skip_turn(s, r), d - 1, alpha, beta)

        maximizing = (s.turn == ai_player)
        node_type = "MAX" if maximizing else "MIN"
        
        best = -inf if maximizing else inf
        best_move = None

        for mv in moves:
            s2 = apply_move(s, r, mv)
            v, _ = value_turn(s2, d - 1, alpha, beta)
            
            if maximizing:
                if v > best:
                    best = v
                    best_move = mv
                if best >= beta:
                    _print_node(f"{node_type}(PRUNED)", d, best, move=best_move, roll=r)
                    return best, best_move
                alpha = max(alpha, best)
            else:
                if v < best:
                    best = v
                    best_move = mv
                if best <= alpha:
                    _print_node(f"{node_type}(PRUNED)", d, best, move=best_move, roll=r)
                    return best, best_move
                beta = min(beta, best)
        
        _print_node(node_type, d, best, move=best_move, roll=r)
        return best, best_move

    moves = legal_moves(state, roll)
    if not moves:
        val, _ = value_turn(skip_turn(state, roll), depth - 1)
        return None, val, stats

    maximizing = (state.turn == ai_player)
    node_type = "MAX" if maximizing else "MIN"
    
    best_mv = None
    best_val = -inf if maximizing else inf
    alpha = -inf
    beta = inf

    for mv in moves:
        s2 = apply_move(state, roll, mv)
        v, _ = value_turn(s2, depth - 1, alpha, beta)
        if maximizing:
            if v > best_val:
                best_val = v
                best_mv = mv
            if best_val >= beta:
                _print_node(f"{node_type}(PRUNED)", depth, best_val, move=best_mv, roll=roll)
                return best_mv, best_val, stats
            alpha = max(alpha, best_val)
        else:
            if v < best_val:
                best_val = v
                best_mv = mv
            if best_val <= alpha:
                _print_node(f"{node_type}(PRUNED)", depth, best_val, move=best_mv, roll=roll)
                return best_mv, best_val, stats
            beta = min(beta, best_val)
    
    _print_node(node_type, depth, best_val, move=best_mv, roll=roll)
    return best_mv, best_val, stats

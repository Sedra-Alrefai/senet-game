
from __future__ import annotations
from dataclasses import dataclass, field
from math import inf
from typing import Optional, Tuple
from game.state import GameState, Player, OUT
from game.rules import legal_moves, apply_move, skip_turn, is_terminal
from game.dice import roll_distribution
from game.move import Move, MoveKind
from game.constants import HAPPINESS, THREE_TRUTHS, RE_ATOUM, HORUS
from .eval import evaluate

@dataclass
class SearchStats:
    nodes: int = 0
    leafs: int = 0
    chosen_eval_value: float = 0.0
    tree_info: list[str] = field(default_factory=list) 

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

def choose_best_move_given_roll(state: GameState, ai_player: Player, depth: int, roll: int, print_tree: bool = False) -> tuple[object, float, SearchStats]:
    stats = SearchStats()
    dist = roll_distribution()
    
    def log_node(node_type: str, depth: int, roll: int | None, value: float, alpha: float | None = None, beta: float | None = None, move: Move | None = None, is_leaf: bool = False):
        if not print_tree:
            return
        indent = "  " * (depth)
        node_info = f"{indent}[{node_type}] Depth={depth}"
        if roll is not None:
            node_info += f", Roll={roll}"
        if move is not None:
            move_str = f"piece#{move.piece_id} {move.kind.value}"
            node_info += f", Move={move_str}"
        if alpha is not None:
            node_info += f", Alpha={alpha:.2f}"
        if beta is not None:
            node_info += f", Beta={beta:.2f}"
        node_info += f", Value={value:.2f}"
        if is_leaf:
            node_info += " [LEAF]"
        stats.tree_info.append(node_info)
    
    def value_turn(s: GameState, d: int, current_roll: int | None = None) -> float:
        stats.nodes += 1
        if d == 0 or is_terminal(s):
            stats.leafs += 1
            eval_val = evaluate(s, ai_player)
            node_type = "EXPECTATION" if current_roll is None else "EVAL"
            log_node(node_type, d, current_roll, eval_val, is_leaf=True)
            return eval_val
        
        node_type = "EXPECTATION"
        log_node(node_type, d, current_roll, 0.0)
        
        exp_val = 0.0
        roll_values = []
        for r, p in dist.items():
            v, _ = value_after_roll(s, d, r, -inf, inf)
            exp_val += p * v
            roll_values.append((r, p, v))
        
        if print_tree:
            indent = "  " * (d)
            for r, p, v in roll_values:
                stats.tree_info.append(f"{indent}  Roll={r}, Prob={p:.3f}, Value={v:.2f}, Weighted={p*v:.2f}")
            stats.tree_info.append(f"{indent}Expected Value={exp_val:.2f}")
        
        log_node(node_type, d, current_roll, exp_val)
        return exp_val
    
    def value_after_roll(s: GameState, d: int, r: int, alpha: float, beta: float) -> Tuple[float, Optional[Move]]:
        raw_moves = legal_moves(s, r)
        moves = filter_suicide_moves(s, raw_moves, r) if s.turn == ai_player else raw_moves

        if not moves:
            skip_val = value_turn(skip_turn(s, r), d - 1, r)
            node_type = "MAX" if s.turn == ai_player else "MIN"
            log_node(node_type, d, r, skip_val, alpha, beta, None)
            return skip_val, None

        maximizing = (s.turn == ai_player)
        node_type = "MAX" if maximizing else "MIN"
        best_val = -inf if maximizing else inf
        best_move = None
        if d >= 1: 
            moves = _order_moves(moves, s, r, ai_player)

        if print_tree:
            indent = "  " * (d)
            stats.tree_info.append(f"{indent}[{node_type}] Depth={d}, Roll={r}, Moves={len(moves)}, Alpha={alpha:.2f}, Beta={beta:.2f}")

        move_values = []
        for mv in moves:
            s2 = apply_move(s, r, mv)
            val = value_turn(s2, d - 1, r)
            move_values.append((mv, val))
            
            if print_tree:
                indent = "  " * (d)
                move_str = f"piece#{mv.piece_id} {mv.kind.value}"
                stats.tree_info.append(f"{indent}  Move={move_str}, Value={val:.2f}")
            
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
                if print_tree:
                    indent = "  " * (d)
                    stats.tree_info.append(f"{indent}  [PRUNED] Alpha={alpha:.2f}, Beta={beta:.2f}")
                break 

        log_node(node_type, d, r, best_val, alpha, beta, best_move)
        return best_val, best_move
    
    raw_moves = legal_moves(state, roll)
    moves = filter_suicide_moves(state, raw_moves, roll) if state.turn == ai_player else raw_moves

    if print_tree:
        stats.tree_info.append(f"=== ROOT: Depth={depth}, Roll={roll}, Turn={state.turn} ===")

    if not moves:
        val = value_turn(skip_turn(state, roll), depth - 1, roll)
        stats.chosen_eval_value = val
        if print_tree:
            stats.tree_info.append(f"=== RESULT: No moves, Value={val:.2f} ===")
        return None, val, stats
    
    moves = _order_moves(moves, state, roll, ai_player)
    
    if print_tree:
        stats.tree_info.append(f"Root moves to evaluate: {len(moves)}")
    
    best_mv = None
    best_val = -inf
    alpha = -inf
    
    for mv in moves:
        s2 = apply_move(state, roll, mv)
        v = value_turn(s2, depth - 1, roll)
        
        if print_tree:
            move_str = f"piece#{mv.piece_id} {mv.kind.value}"
            stats.tree_info.append(f"Root Move={move_str}, Value={v:.2f}")
        
        if v > best_val:
            best_val = v
            best_mv = mv
        
        alpha = max(alpha, best_val)

    stats.chosen_eval_value = best_val
    
    if print_tree:
        if best_mv:
            move_str = f"piece#{best_mv.piece_id} {best_mv.kind.value}"
            stats.tree_info.append(f"=== RESULT: Best Move={move_str}, Value={best_val:.2f} ===")
        else:
            stats.tree_info.append(f"=== RESULT: No move, Value={best_val:.2f} ===")

    return best_mv, best_val, stats
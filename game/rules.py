from __future__ import annotations
from dataclasses import replace
from .state import GameState, Player, OUT
from .move import Move, MoveKind
from .constants import (
    NUM_SQUARES, REBIRTH, HAPPINESS, WATER, THREE_TRUTHS, RE_ATOUM, HORUS,
)

def initial_state() -> GameState:
   
    black = []
    white = []
    for i in range(1, 15):
        if i % 2 == 1:
            black.append(i)
        else:
            white.append(i)
    return GameState(black=tuple(black), white=tuple(white), turn=Player.BLACK, pending=None)

def is_terminal(state: GameState) -> bool:
    return all(p == OUT for p in state.black) or all(p == OUT for p in state.white)

def winner(state: GameState) -> Player | None:
    if all(p == OUT for p in state.black):
        return Player.BLACK
    if all(p == OUT for p in state.white):
        return Player.WHITE
    return None

def _occupied_map(state: GameState) -> dict[int, tuple[Player, int]]:
   
    occ = {}
    for pid, pos in enumerate(state.black):
        if pos != OUT:
            occ[pos] = (Player.BLACK, pid)
    for pid, pos in enumerate(state.white):
        if pos != OUT:
            occ[pos] = (Player.WHITE, pid)
    return occ

def _send_to_rebirth(state: GameState, p: Player, piece_id: int) -> GameState:
    
    occ = _occupied_map(state)
    current_pos = state.pieces_of(p)[piece_id]
    
    target = REBIRTH
    if target not in occ:
        positions = list(state.pieces_of(p))
        positions[piece_id] = target
        return state.set_pieces_of(p, tuple(positions))
    
    target = None
    for s in range(REBIRTH - 1, 0, -1):
        if s not in occ:
            target = s
            break
    
    if target is None:
        for s in range(REBIRTH + 1, NUM_SQUARES + 1):
            if s not in occ:
                target = s
                break
    
    if target is None:
        target = current_pos
    
    if target in occ:
        for s in range(1, NUM_SQUARES + 1):
            if s not in occ:
                target = s
                break
        if target is None or target in occ:
            target = current_pos
    
    positions = list(state.pieces_of(p))
    positions[piece_id] = target
    
    if target < 1 or target > NUM_SQUARES:
        raise RuntimeError(f"Invalid rebirth target: {target} (must be 1-{NUM_SQUARES})")
    
    return state.set_pieces_of(p, tuple(positions))

def _apply_swap_if_needed(state: GameState, mover: Player, from_sq: int, to_sq: int) -> GameState:
  
    if to_sq > HAPPINESS:
        return state

    occ = _occupied_map(state)
    if to_sq not in occ:
        return state

    op, op_pid = occ[to_sq]
    if op == mover:
        return state

    mover_positions = list(state.pieces_of(mover))
    opp_positions = list(state.pieces_of(op))

    mover_pid = None
    for pid, pos in enumerate(mover_positions):
        if pos == from_sq:
            mover_pid = pid
            break
    if mover_pid is None:
        return state

    mover_positions[mover_pid] = to_sq
    opp_positions[op_pid] = from_sq

    state = state.set_pieces_of(mover, tuple(mover_positions))
    state = state.set_pieces_of(op, tuple(opp_positions))
    return state

def _happiness_block_rule(from_sq: int, to_sq: int) -> bool:
    """
    Absolute rule:
    If moving would cross beyond 26 without landing exactly on 26 => illegal.
    I.e., if from < 26 and to > 26 then only legal if to == 26.
    """
    if from_sq < HAPPINESS and to_sq > HAPPINESS:
        return False  # would jump over happiness
    return True

def legal_moves(state: GameState, roll: int) -> list[Move]:
    """
    Returns list of legal moves for the current player for a given roll in 1..5.
    Includes PROMOTE moves (from 26 with roll 5, or pending-exit squares).
    """
    if is_terminal(state):
        return []

    p = state.turn
    my = state.pieces_of(p)
    occ = _occupied_map(state)

    moves: list[Move] = []

    pending_piece = None
    pending_req = None
    if state.pending and state.pending[0] == p:
        _, pending_piece, pending_req = state.pending

        if my[pending_piece] in (THREE_TRUTHS, RE_ATOUM, HORUS):
            if pending_req is None or roll == pending_req:
                moves.append(Move(piece_id=pending_piece, kind=MoveKind.PROMOTE))

    for pid, from_sq in enumerate(my):
        if from_sq == OUT:
            continue

        if from_sq == HAPPINESS and roll == 5:
            moves.append(Move(piece_id=pid, kind=MoveKind.PROMOTE))
            continue

        if from_sq == THREE_TRUTHS:
            if roll != 3:
                continue

        if from_sq == RE_ATOUM:
            if roll != 2:
                continue

        to_sq = from_sq + roll
        if to_sq > NUM_SQUARES:
            continue

        if from_sq == THREE_TRUTHS and roll == 2 and to_sq == HORUS:
            continue

        if not _happiness_block_rule(from_sq, to_sq):
            continue

        if to_sq in occ and occ[to_sq][0] == p:
            continue

        if to_sq in occ and occ[to_sq][0] != p and to_sq > HAPPINESS:
            continue

        moves.append(Move(piece_id=pid, kind=MoveKind.MOVE))

    return moves

def apply_move(state: GameState, roll: int, move: Move) -> GameState:
  
    if move not in legal_moves(state, roll):
        raise ValueError("Illegal move")

    p = state.turn
    my = list(state.pieces_of(p))

    if state.pending and state.pending[0] == p:
        _, pend_pid, pend_req = state.pending

        if not (move.kind == MoveKind.PROMOTE and move.piece_id == pend_pid and
                (pend_req is None or roll == pend_req)):
            state = _send_to_rebirth(state, p, pend_pid)
        state = replace(state, pending=None)
        my = list(state.pieces_of(p))
    
    for pid, from_sq in enumerate(my):
        if from_sq == OUT:
            continue
        
        if from_sq == THREE_TRUTHS and roll != 3:
            if not (move.kind == MoveKind.PROMOTE and move.piece_id == pid):
                state = _send_to_rebirth(state, p, pid)
                my = list(state.pieces_of(p))
        
        if from_sq == RE_ATOUM and roll != 2:
            if not (move.kind == MoveKind.PROMOTE and move.piece_id == pid):
                state = _send_to_rebirth(state, p, pid)
                my = list(state.pieces_of(p))

    if move.kind == MoveKind.PROMOTE:
        my[move.piece_id] = OUT
        state = state.set_pieces_of(p, tuple(my))
        return state.swap_turn()

    from_sq = my[move.piece_id]
    to_sq = from_sq + roll

    occ = _occupied_map(state)
    if to_sq in occ and occ[to_sq][0] != p:
        if to_sq <= HAPPINESS:
            state = _apply_swap_if_needed(state, p, from_sq, to_sq)
            my = list(state.pieces_of(p))
        else:
            raise ValueError("Illegal: cannot capture beyond 26")
    else:
        my[move.piece_id] = to_sq
        state = state.set_pieces_of(p, tuple(my))

    my = list(state.pieces_of(p))
    landed = my[move.piece_id]

    if landed == WATER:
        state = _send_to_rebirth(state, p, move.piece_id)
    else:
        landed = state.pieces_of(p)[move.piece_id]
        if landed == THREE_TRUTHS:
            state = replace(state, pending=(p, move.piece_id, 3))
        elif landed == RE_ATOUM:
            state = replace(state, pending=(p, move.piece_id, 2))
        elif landed == HORUS:
            state = replace(state, pending=(p, move.piece_id, None))

    return state.swap_turn()

def skip_turn(state: GameState, roll: int) -> GameState:
  
    from game.constants import THREE_TRUTHS, RE_ATOUM
    
    p = state.turn
    my = list(state.pieces_of(p))
    
    if state.pending and state.pending[0] == p:
        _, pend_pid, _ = state.pending
        state = _send_to_rebirth(state, p, pend_pid)
        state = replace(state, pending=None)
        my = list(state.pieces_of(p))
    
    for pid, from_sq in enumerate(my):
        if from_sq == OUT:
            continue
        
        if from_sq == THREE_TRUTHS and roll != 3:
            state = _send_to_rebirth(state, p, pid)
            my = list(state.pieces_of(p))
        
        if from_sq == RE_ATOUM and roll != 2:
            state = _send_to_rebirth(state, p, pid)
            my = list(state.pieces_of(p))
    
    return state.swap_turn()

from __future__ import annotations
import tkinter as tk
from dataclasses import dataclass

from game.rules import initial_state, legal_moves, apply_move, skip_turn, is_terminal, winner
from game.state import Player, OUT
from game.dice import toss_sticks
from game.path import index_to_cell, cell_to_index
from game.constants import BOARD_COLS, BOARD_ROWS

from ai.expectiminimax import choose_best_move_given_roll
from game.move import Move, MoveKind

CELL_SIZE = 85
PADDING = 20

EXIT_BOX_W = 180
EXIT_BOX_H = 250

AI_PLAYER = Player.WHITE
DEFAULT_DEPTH = 2


@dataclass
class UiState:
    roll: int | None = None
    selected_piece: int | None = None
    expected_dest: int | None = None
    human_player: Player = Player.BLACK
    last_ai_nodes: int = 0
    ai_move_from: int | None = None
    ai_move_to: int | None = None
    available_promote_pieces: list[int] | None = None


class SenetTkUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Senet (Human vs AI)")

        self.state = initial_state()
        self.ui = UiState()

        self._build_layout()
        self._render_all()
        self._check_end_or_prompt()

    def _build_layout(self):
        top = tk.Frame(self.root)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        scores_frame = tk.Frame(top)
        scores_frame.pack(side=tk.LEFT, padx=10)
        
        self.lbl_black_score = tk.Label(scores_frame, text="Black: 0", font=("Arial", 11, "bold"))
        self.lbl_black_score.pack()
        self.black_score_box = tk.Canvas(scores_frame, bg="#f5e6d3", width=80, height=30, highlightthickness=0, relief=tk.FLAT)
        self.black_score_box.pack(pady=2)
        
        self.lbl_white_score = tk.Label(scores_frame, text="White: 0", font=("Arial", 11, "bold"))
        self.lbl_white_score.pack()
        self.white_score_box = tk.Canvas(scores_frame, bg="#f5e6d3", width=80, height=30, highlightthickness=0, relief=tk.FLAT)
        self.white_score_box.pack(pady=2)

        title_label = tk.Label(top, text="Senet", font=("Arial", 18, "bold"))
        title_label.pack(side=tk.LEFT, padx=30)
        
        turn_frame = tk.Frame(top)
        turn_frame.pack(side=tk.LEFT, padx=10)
        self.lbl_turn = tk.Label(turn_frame, text="White's turn", font=("Arial", 12))
        self.lbl_turn.pack()

        self.btn_toss = tk.Button(top, text="Toss!", command=self.on_toss, state=tk.DISABLED)
        self.btn_toss.pack(side=tk.LEFT, padx=5)
        self.btn_toss.pack_forget()

        self.lbl_roll = tk.Label(top, text="Roll: -", font=("Arial", 12))
        self.lbl_roll.pack(side=tk.LEFT, padx=10)
        
        sticks_frame = tk.Frame(top, bg="#f5e6d3", relief=tk.RAISED, borderwidth=2)
        sticks_frame.pack(side=tk.LEFT, padx=10)
        
        self.sticks_canvas = tk.Canvas(sticks_frame, width=70, height=90, bg="#f5e6d3", highlightthickness=0, cursor="hand2")
        self.sticks_canvas.pack(padx=8, pady=8)
        self.sticks_canvas.bind("<Button-1>", self.on_sticks_click)
        
        tk.Label(sticks_frame, text="Click to toss!", font=("Arial", 9, "bold"), bg="#f5e6d3", fg="#8b4513").pack()

        self.btn_skip = tk.Button(top, text="Skip turn", command=self.on_skip, state=tk.DISABLED)
        self.btn_skip.pack(side=tk.LEFT, padx=5)

        self.btn_select = tk.Button(top, text="Select a piece", state=tk.DISABLED)
        self.btn_select.pack(side=tk.LEFT, padx=5)
        
        self.btn_promote = tk.Button(top, text="Promote", command=self.on_promote, state=tk.DISABLED)
        self.btn_promote.pack(side=tk.LEFT, padx=5)

        ai_control_frame = tk.Frame(top)
        ai_control_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(ai_control_frame, text="AI Depth:", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)
        
        self.depth_var = tk.IntVar(value=DEFAULT_DEPTH)
        self.depth_slider = tk.Scale(
            ai_control_frame,
            from_=1,
            to=5,
            orient=tk.HORIZONTAL,
            variable=self.depth_var,
            length=100,
            font=("Arial", 9)
        )
        self.depth_slider.pack(side=tk.LEFT, padx=2)
        
        self.lbl_depth_value = tk.Label(ai_control_frame, text=str(DEFAULT_DEPTH), font=("Arial", 10, "bold"))
        self.lbl_depth_value.pack(side=tk.LEFT, padx=2)
        
        self.depth_slider.configure(command=self._on_depth_change)
        
        self.lbl_ai_nodes = tk.Label(ai_control_frame, text="Nodes: 0", font=("Arial", 9), fg="blue")
        self.lbl_ai_nodes.pack(side=tk.LEFT, padx=10)

        self.msg = tk.Label(self.root, text="", anchor="w", justify="left", fg="darkgreen", font=("Arial", 11, "bold"))
        self.msg.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        board_width = PADDING * 2 + BOARD_COLS * CELL_SIZE
        board_height = PADDING * 2 + BOARD_ROWS * CELL_SIZE
        w = board_width + 20 + EXIT_BOX_W
        h = board_height + 50
        
        self.canvas = tk.Canvas(self.root, width=w, height=h, bg="#808080")
        self.canvas.pack(side=tk.TOP, padx=10, pady=10)
        
        self.root.geometry(f"{w + 50}x{h + 200}")

        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def _set_status(self, text: str, error: bool = False):
        self.msg.configure(text="", fg=("red" if error else "darkgreen"))
    
    def _on_depth_change(self, value: str):
        """Callback when depth slider changes."""
        depth = int(value)
        self.lbl_depth_value.configure(text=str(depth))

    def _count_out(self):
        black_out = sum(1 for p in self.state.black if p == OUT)
        white_out = sum(1 for p in self.state.white if p == OUT)
        return black_out, white_out
    
    def _update_score_boxes(self, black_count: int, white_count: int):
        """Update the score boxes with circles representing exited pieces"""
        self.black_score_box.delete("all")
        self.lbl_black_score.configure(text=f"Black: {black_count}")
        
        box_width = 80
        box_height = 30
        circle_radius = 8
        spacing = 12
        
        max_visible = min(black_count, 7)
        total_width = max_visible * spacing
        start_x = (box_width - total_width) // 2 + circle_radius
        
        for i in range(max_visible):
                x = start_x + i * spacing
                y = box_height // 2
                self.black_score_box.create_oval(
                    x - circle_radius, y - circle_radius,
                    x + circle_radius, y + circle_radius,
                    fill="#708090", outline="#000000", width=0.4
                )
        
        self.white_score_box.delete("all")
        self.lbl_white_score.configure(text=f"White: {white_count}")
        
        max_visible_white = min(white_count, 7)
        total_width_white = max_visible_white * spacing
        start_x_white = (box_width - total_width_white) // 2 + circle_radius
        
        for i in range(max_visible_white):
                x = start_x_white + i * spacing
                y = box_height // 2
                self.white_score_box.create_oval(
                    x - circle_radius, y - circle_radius,
                    x + circle_radius, y + circle_radius,
                    fill="#FFFAFA", outline="#000000", width=0.4
                )

    def _draw_special_square_icon(self, canvas, x1, y1, x2, y2, square: int):
        """Draw special square icons (15, 26-30)"""
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        icon_color = "#000000"
        
        if square == 15:
            self.canvas.create_oval(cx - 10, cy - 20, cx + 10, cy - 5, outline=icon_color, width=2)
            self.canvas.create_line(cx, cy - 5, cx, cy + 15, width=3, fill=icon_color)
            self.canvas.create_line(cx - 8, cy + 5, cx + 8, cy + 5, width=3, fill=icon_color)
        
        elif square == 26:
            for i in range(3):
                x = cx - 15 + i * 15
                self.canvas.create_line(x, cy - 18, x, cy + 12, width=3, fill=icon_color)
                self.canvas.create_rectangle(x - 4, cy - 20, x + 4, cy - 12, outline=icon_color, width=2)
        
        elif square == 27:
            for wave_y in range(3):
                y = cy - 10 + wave_y * 10
                points = []
                for i in range(7):
                    x = x1 + 8 + i * (CELL_SIZE - 16) // 6
                    y_offset = 4 * (1 if i % 2 == 0 else -1)
                    points.extend([x, y + y_offset])
                if len(points) >= 4:
                    self.canvas.create_line(points, width=2, fill=icon_color, smooth=True)
        
        elif square == 28:
            for i in range(3):
                x = cx - 18 + i * 18
                self.canvas.create_rectangle(x - 5, cy - 8, x + 5, cy + 8, outline=icon_color, width=2)
                self.canvas.create_oval(x - 3, cy - 12, x + 3, cy - 6, outline=icon_color, width=2)
                self.canvas.create_arc(x - 8, cy - 5, x + 2, cy + 5, start=0, extent=180, outline=icon_color, width=2, style=tk.ARC)
        
        elif square == 29:
            for i in range(2):
                x = cx - 12 + i * 24
                self.canvas.create_oval(x - 5, cy - 18, x + 5, cy - 8, outline=icon_color, width=2)
                self.canvas.create_rectangle(x - 4, cy - 8, x + 4, cy + 5, outline=icon_color, width=2)
                self.canvas.create_arc(x - 8, cy + 2, x, cy + 12, start=0, extent=90, outline=icon_color, width=2, style=tk.ARC)
                self.canvas.create_arc(x, cy + 2, x + 8, cy + 12, start=90, extent=90, outline=icon_color, width=2, style=tk.ARC)
        
        elif square == 30:
            self.canvas.create_oval(cx - 15, cy - 15, cx + 15, cy + 15, outline=icon_color, width=2)
            self.canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, outline=icon_color, width=2)
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=icon_color, outline=icon_color)

    def _draw_game_over_overlay(self):
        """Draw Game Over overlay on the canvas"""
        if not is_terminal(self.state):
            return
        
        w = winner(self.state)
        b_out, w_out = self._count_out()
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        self.canvas.create_rectangle(
            0, 0, canvas_width, canvas_height,
            fill="black", outline="", stipple="gray50"
        )
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        if w == self.ui.human_player:
            self.canvas.create_text(
                center_x, center_y - 80,
                text="🎉 CONGRATULATIONS! 🎉",
                font=("Arial", 36, "bold"),
                fill="gold"
            )
            winner_text = "You Won! 🏆"
            winner_color = "green"
        else:
            self.canvas.create_text(
                center_x, center_y - 60,
                text="🎮 GAME OVER 🎮",
                font=("Arial", 32, "bold"),
                fill="red"
            )
            winner_text = "AI Won! 🤖"
            winner_color = "orange"
        
        self.canvas.create_text(
            center_x, center_y,
            text=winner_text,
            font=("Arial", 24, "bold"),
            fill=winner_color
        )
        
        score_text = f"Black: {b_out}/7 | White: {w_out}/7"
        self.canvas.create_text(
            center_x, center_y + 40,
            text=score_text,
            font=("Arial", 18),
            fill="white"
        )

    def _render_all(self):
        self.canvas.delete("all")

        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                x1 = PADDING + c * CELL_SIZE
                y1 = PADDING + r * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                
                fill = "#F5F5DC" if (r + c) % 2 == 0 else "#DEB887"
                
                idx = cell_to_index(r, c)
                
                highlight = False
                if idx == self.ui.ai_move_from or idx == self.ui.ai_move_to:
                    fill = "#90EE90"
                    highlight = True
                
                radius = 4
                self.canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="", width=0)
                self.canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="", width=0)
                self.canvas.create_oval(x1, y1, x1 + radius*2, y1 + radius*2, fill=fill, outline="", width=0)
                self.canvas.create_oval(x2 - radius*2, y1, x2, y1 + radius*2, fill=fill, outline="", width=0)
                self.canvas.create_oval(x1, y2 - radius*2, x1 + radius*2, y2, fill=fill, outline="", width=0)
                self.canvas.create_oval(x2 - radius*2, y2 - radius*2, x2, y2, fill=fill, outline="", width=0)
                self.canvas.create_line(x1 + radius, y1, x2 - radius, y1, fill="#000000", width=0.5)
                self.canvas.create_line(x1 + radius, y2, x2 - radius, y2, fill="#000000", width=0.5)
                self.canvas.create_line(x1, y1 + radius, x1, y2 - radius, fill="#000000", width=0.5)
                self.canvas.create_line(x2, y1 + radius, x2, y2 - radius, fill="#000000", width=0.5)
                self.canvas.create_arc(x1, y1, x1 + radius*2, y1 + radius*2, start=90, extent=90, outline="#000000", width=0.5, style=tk.ARC)
                self.canvas.create_arc(x2 - radius*2, y1, x2, y1 + radius*2, start=0, extent=90, outline="#000000", width=0.5, style=tk.ARC)
                self.canvas.create_arc(x1, y2 - radius*2, x1 + radius*2, y2, start=180, extent=90, outline="#000000", width=0.5, style=tk.ARC)
                self.canvas.create_arc(x2 - radius*2, y2 - radius*2, x2, y2, start=270, extent=90, outline="#000000", width=0.5, style=tk.ARC)

                if idx in (15, 26, 27, 28, 29, 30):
                    self.canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline="#2a9d8f", width=3)
                    self._draw_special_square_icon(self.canvas, x1, y1, x2, y2, idx)

        bx1 = PADDING + BOARD_COLS * CELL_SIZE + 30
        by1 = PADDING
        bx2 = bx1 + EXIT_BOX_W
        by2 = by1 + EXIT_BOX_H
        
        exit_available = False
        if self.state.turn == self.ui.human_player and self.ui.roll is not None:
            mvs = legal_moves(self.state, self.ui.roll)
            exit_available = any(m.kind == MoveKind.PROMOTE for m in mvs)
        
        exit_fill = "#90EE90" if exit_available else "#f8f9fa"
        exit_outline = "#2a9d8f" if exit_available else "#333"
        exit_width = 4 if exit_available else 2
        
        self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=exit_fill, outline=exit_outline, width=exit_width)
        exit_text = "EXIT (Click!)" if exit_available else "EXIT"
        self.canvas.create_text((bx1 + bx2) // 2, by1 + 20, text=exit_text, font=("Arial", 14, "bold"))
        
        b_out, w_out = self._count_out()
        exit_y = by1 + 50
        piece_radius = 20
        spacing = 30
        max_visible = 7
        
        for i in range(min(b_out, max_visible)):
            y = exit_y + i * spacing
            cx = bx1 + 40
            self.canvas.create_oval(cx - piece_radius, y, cx + piece_radius, y + piece_radius * 2, 
                                   fill="#708090", outline="#000000", width=0.4)
        
        for i in range(min(w_out, max_visible)):
            y = exit_y + i * spacing
            cx = bx1 + 120
            self.canvas.create_oval(cx - piece_radius, y, cx + piece_radius, y + piece_radius * 2, 
                                   fill="#FFFAFA", outline="#000000", width=0.4)

        if self.ui.expected_dest is not None:
            cell = index_to_cell(self.ui.expected_dest)
            x1 = PADDING + cell.col * CELL_SIZE
            y1 = PADDING + cell.row * CELL_SIZE
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            self.canvas.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3, outline="#90EE90", width=4)

        self._draw_pieces(Player.BLACK, self.state.black)
        self._draw_pieces(Player.WHITE, self.state.white)

        turn_text = "White's turn" if self.state.turn == Player.WHITE else "Black's turn"
        self.lbl_turn.configure(text=turn_text)
        roll_txt = "-" if self.ui.roll is None else str(self.ui.roll)
        self.lbl_roll.configure(text=f"Roll: {roll_txt}")

        b_out, w_out = self._count_out()

        self._update_score_boxes(b_out, w_out)

        self.lbl_ai_nodes.configure(text=f"Nodes: {self.ui.last_ai_nodes}")

        if is_terminal(self.state):
            self._draw_game_over_overlay()

        if self.state.turn == self.ui.human_player and self.ui.roll is not None:
            mvs = legal_moves(self.state, self.ui.roll)
            self.btn_skip.configure(state=(tk.NORMAL if not mvs else tk.DISABLED))
            has_promote = any(m.kind == MoveKind.PROMOTE for m in mvs)
            self.btn_promote.configure(state=(tk.NORMAL if has_promote else tk.DISABLED))
            self.btn_select.configure(state=tk.DISABLED)
            
            promote_pieces = [m.piece_id for m in mvs if m.kind == MoveKind.PROMOTE]
            self.ui.available_promote_pieces = promote_pieces if promote_pieces else []
            
            if has_promote:
                my_pieces = self.state.pieces_of(self.ui.human_player)
                promote_info = []
                for pid in promote_pieces:
                    pos = my_pieces[pid]
                    if pos == 26:
                        promote_info.append(f"Piece #{pid} on square 26 - click EXIT or Promote to exit")
                    elif pos == 28:
                        promote_info.append(f"Piece #{pid} on square 28 - click EXIT or Promote to exit")
                    elif pos == 29:
                        promote_info.append(f"Piece #{pid} on square 29 - click EXIT or Promote to exit")
                    elif pos == 30:
                        promote_info.append(f"Piece #{pid} on square 30 - click EXIT or Promote to exit")
                if promote_info:
                    self._set_status(" | ".join(promote_info))
        else:
            self.btn_skip.configure(state=tk.DISABLED)
            self.btn_promote.configure(state=tk.DISABLED)
            self.btn_select.configure(state=tk.DISABLED)
            self.ui.available_promote_pieces = []

        if self.state.turn == self.ui.human_player and self.ui.roll is None and not is_terminal(self.state):
            self.sticks_canvas.configure(cursor="hand2")
        else:
            self.sticks_canvas.configure(cursor="arrow")

    def _draw_pieces(self, player: Player, positions: tuple[int, ...]):
        for pid, pos in enumerate(positions):
            if pos == OUT:
                continue
            cell = index_to_cell(pos)
            cx = PADDING + cell.col * CELL_SIZE + CELL_SIZE // 2
            cy = PADDING + cell.row * CELL_SIZE + CELL_SIZE // 2

            r = 25
            if player == Player.WHITE:
                fill = "#FFFAFA"
                outline = "#000000"
                outline_width = 1
            else:
                fill = "#708090"
                outline = "#000000"
                outline_width = 0.5

            if self.ui.selected_piece == pid and self.state.turn == self.ui.human_player and player == self.ui.human_player:
                self.canvas.create_oval(cx - (r + 6), cy - (r + 6), cx + (r + 6), cy + (r + 6), outline="#90EE90", width=4)

            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=outline_width)

    def on_toss(self):
        if is_terminal(self.state):
            return

        if self.state.turn != self.ui.human_player:
            self._set_status("Cannot roll now. It's AI's turn.", error=True)
            return

        if self.ui.roll is not None:
            self._set_status("Already rolled. Choose a move or press Skip/Promote if needed.", error=True)
            return

        self.ui.roll = toss_sticks()
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._draw_sticks(self.ui.roll)
        self._render_all()

        self._set_status("Your turn: Choose a piece (you can change selection) then click the highlighted square to move, or Promote to exit.")
    
    def on_sticks_click(self, event):
        """Click on sticks area to roll"""
        if is_terminal(self.state):
            return
        
        if self.state.turn != self.ui.human_player:
            self._set_status("Cannot roll now. It's AI's turn.", error=True)
            return

        if self.ui.roll is not None:
            self._set_status("Already rolled. Choose a move or press Skip/Promote if needed.", error=True)
            return

        self.ui.roll = toss_sticks()
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._draw_sticks(self.ui.roll)
        self._render_all()

        self._set_status("Your turn: Choose a piece (you can change selection) then click the highlighted square to move, or Promote to exit.")
    
    def _draw_sticks(self, roll: int):
        """Draw sticks in sticks area - dark/light pattern"""
        self.sticks_canvas.delete("all")
        
        stick_values = []
        if roll is None:
            stick_values = [0, 0, 0, 0]
        elif roll == 5:
            stick_values = [0, 0, 0, 0]
        else:
            stick_values = [1 if i < roll else 0 for i in range(4)]
        
        stick_width = 8
        stick_height = 60
        spacing = 14
        start_x = 15
        start_y = 15
        
        for i in range(4):
            x = start_x + i * spacing
            y1 = start_y
            y2 = start_y + stick_height
            
            if stick_values[i] == 1:
                stick_color = "#8b4513"
                outline_color = "#654321"
            else:
                stick_color = "#f5e6d3"
                outline_color = "#d2b48c"
            self.sticks_canvas.create_rectangle(
                x - stick_width//2, y1,
                x + stick_width//2, y2,
                fill=stick_color,
                outline=outline_color,
                width=2
            )

    def _ai_toss_and_play(self):
        if is_terminal(self.state):
            return
        if self.state.turn == self.ui.human_player:
            return
        if self.ui.roll is not None:
            return

        self._set_status("AI's turn...")
        self.ui.roll = toss_sticks()
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._draw_sticks(self.ui.roll)
        self._render_all()

        self.root.after(200, self._ai_play)

    def _ai_play(self):
        if is_terminal(self.state):
            return
        roll = self.ui.roll
        if roll is None:
            return

        search_depth = self.depth_var.get()

        mv, val, stats = choose_best_move_given_roll(self.state, AI_PLAYER, search_depth, roll)

        self.ui.last_ai_nodes = stats.nodes

        if mv is None:
            self.state = skip_turn(self.state, roll)
            self._set_status(f"AI: No legal moves -> Skip | nodes={stats.nodes}, leafs={stats.leafs}, val={val:.2f}")
            self.ui.ai_move_from = None
            self.ui.ai_move_to = None
        else:
            my_pieces = self.state.pieces_of(AI_PLAYER)
            self.ui.ai_move_from = my_pieces[mv.piece_id]
            
            if mv.kind == MoveKind.PROMOTE:
                self.ui.ai_move_to = None
            else:
                self.ui.ai_move_to = self.ui.ai_move_from + roll
            
            self._render_all()
            self.root.update()
            self.root.after(1000, lambda: self._complete_ai_move(mv, roll, stats, val))
            return

        self.ui.roll = None
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._render_all()
        self._check_end_or_prompt()
    
    def _complete_ai_move(self, mv: Move, roll: int, stats, val: float):
        """Complete AI move after highlighting"""
        self.state = apply_move(self.state, roll, mv)
        self._set_status(f"AI played: {mv.kind.value} piece#{mv.piece_id} | nodes={stats.nodes}, leafs={stats.leafs}, val={val:.2f}")
        
        self.ui.roll = None
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self.ui.ai_move_from = None
        self.ui.ai_move_to = None
        self._render_all()
        self._check_end_or_prompt()

    def on_skip(self):
        if self.state.turn != self.ui.human_player:
            self._set_status("Not your turn.", error=True)
            return
        if self.ui.roll is None:
            self._set_status("Cannot Skip before rolling.", error=True)
            return
        if legal_moves(self.state, self.ui.roll):
            self._set_status("Cannot Skip while legal moves exist.", error=True)
            return

        self.state = skip_turn(self.state, self.ui.roll)
        self.ui.roll = None
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._render_all()
        self._check_end_or_prompt()

    def on_promote(self):
        if is_terminal(self.state):
            return
        if self.state.turn != self.ui.human_player:
            self._set_status("Not your turn.", error=True)
            return
        if self.ui.roll is None:
            self._set_status("Cannot Promote before rolling.", error=True)
            return

        roll = self.ui.roll
        mvs = legal_moves(self.state, roll)
        promote_moves = [m for m in mvs if m.kind == MoveKind.PROMOTE]
        if not promote_moves:
            self._set_status("No promotion move available with this roll.", error=True)
            return

        chosen = None
        if self.ui.selected_piece is not None:
            for m in promote_moves:
                if m.piece_id == self.ui.selected_piece:
                    chosen = m
                    break
            if chosen is None:
                self._set_status("Selected piece cannot exit. Choose the correct piece or deselect.", error=True)
                return
        else:
            chosen = promote_moves[0]

        try:
            self.state = apply_move(self.state, roll, chosen)
        except Exception as e:
            self._set_status(f"Error: {e}", error=True)
            return

        self._set_status(f"Exited piece #{chosen.piece_id} ✅")
        self.ui.roll = None
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._render_all()
        self._check_end_or_prompt()

    def _check_end_or_prompt(self):
        if is_terminal(self.state):
            w = winner(self.state)
            b_out, w_out = self._count_out()
            if w == self.ui.human_player:
                game_over_text = f"🎉 CONGRATULATIONS! 🎉\nYou Won! 🏆\nBlack: {b_out}/7 | White: {w_out}/7"
            else:
                game_over_text = f"🎮 GAME OVER 🎮\nAI Won! 🤖\nBlack: {b_out}/7 | White: {w_out}/7"
            
            self._set_status(game_over_text, error=False)
            
            self.btn_toss.configure(state=tk.DISABLED)
            self.btn_skip.configure(state=tk.DISABLED)
            self.btn_promote.configure(state=tk.DISABLED)
            self.btn_select.configure(state=tk.DISABLED)
            
            self._draw_game_over_overlay()
            return

        if self.state.turn == self.ui.human_player:
            self._set_status("Your turn: Click to roll sticks.")
            self.btn_toss.configure(state=(tk.NORMAL if self.ui.roll is None else tk.DISABLED))
        else:
            self.btn_toss.configure(state=tk.DISABLED)
            self.root.after(200, self._ai_toss_and_play)

    def on_canvas_click(self, event):
        if is_terminal(self.state):
            return
        if self.state.turn != self.ui.human_player:
            return
        if self.ui.roll is None:
            return

        x = event.x
        y = event.y
        
        bx1 = PADDING + BOARD_COLS * CELL_SIZE + 30
        by1 = PADDING
        bx2 = bx1 + EXIT_BOX_W
        by2 = by1 + EXIT_BOX_H
        
        if bx1 <= x <= bx2 and by1 <= y <= by2:
            if self.ui.available_promote_pieces:
                pid = self.ui.available_promote_pieces[0]
                roll = self.ui.roll
                mv = Move(piece_id=pid, kind=MoveKind.PROMOTE)
                try:
                    self.state = apply_move(self.state, roll, mv)
                    self._set_status(f"Exited piece #{pid} ✅")
                    self.ui.roll = None
                    self.ui.selected_piece = None
                    self.ui.expected_dest = None
                    self.ui.available_promote_pieces = []
                    self._render_all()
                    self._check_end_or_prompt()
                except Exception as e:
                    self._set_status(f"Error: {e}", error=True)
            else:
                self._set_status("Cannot exit now. No exit move available.", error=True)
            return
        
        col = (x - PADDING) // CELL_SIZE
        row = (y - PADDING) // CELL_SIZE
        if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
            return
        sq = cell_to_index(int(row), int(col))
        if sq is None:
            return

        human_pid = self._human_piece_on_square(sq)
        if human_pid is not None:
            if self.ui.selected_piece == human_pid:
                self.ui.selected_piece = None
                self.ui.expected_dest = None
                self._render_all()
                self._set_status("Piece selection cancelled. Choose another piece.")
                return

            roll = self.ui.roll
            dest = self._compute_destination_for_piece(human_pid, roll)

            self.ui.selected_piece = human_pid
            self.ui.expected_dest = dest
            self._render_all()

            mvs = legal_moves(self.state, roll)
            if Move(piece_id=human_pid, kind=MoveKind.PROMOTE) in mvs:
                self._set_status(f"Piece #{human_pid} can exit! Click EXIT box or Promote button to exit.")
            elif dest is None:
                self._set_status("This piece has no move with this roll. If it can exit, use Promote button or click EXIT.")
            else:
                self._set_status("Now click the highlighted square (move destination) to execute the move.")
            return

        if self.ui.selected_piece is None:
            self._set_status("Click one of your pieces first (or use Promote if available).", error=True)
            return

        if self.ui.expected_dest is None:
            self._set_status("This piece has no move with this roll. If it can exit, use Promote.", error=True)
            return

        if sq != self.ui.expected_dest:
            self._set_status("Illegal move: must click the highlighted square only.", error=True)
            return

        pid = self.ui.selected_piece
        roll = self.ui.roll
        mv = Move(piece_id=pid, kind=MoveKind.MOVE)

        try:
            self.state = apply_move(self.state, roll, mv)
        except Exception as e:
            self._set_status(f"Error: {e}", error=True)
            return

        self._set_status(f"Moved piece #{pid}.")
        self.ui.roll = None
        self.ui.selected_piece = None
        self.ui.expected_dest = None
        self._render_all()
        self._check_end_or_prompt()

    def _human_piece_on_square(self, sq: int) -> int | None:
        pos = self.state.pieces_of(self.ui.human_player)
        for pid, p in enumerate(pos):
            if p == sq:
                return pid
        return None

    def _compute_destination_for_piece(self, pid: int, roll: int) -> int | None:
        """Calculate destination for piece. Returns None if exit is available or no move."""
        mvs = legal_moves(self.state, roll)
        
        # Check if promotion is available for this piece
        if Move(piece_id=pid, kind=MoveKind.PROMOTE) in mvs:
            return None  # Promotion available - no destination square
        
        if Move(piece_id=pid, kind=MoveKind.MOVE) not in mvs:
            return None
        
        from_pos = self.state.pieces_of(self.ui.human_player)[pid]
        to_sq = from_pos + roll
        
        if from_pos == 28 and roll == 2:
            if to_sq == 30:
                return None
        
        return to_sq

    def run(self):
        self.root.mainloop()

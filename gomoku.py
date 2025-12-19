import tkinter as tk
from tkinter import messagebox
import random
from dataclasses import dataclass

# ----------------------------
# Config
# ----------------------------
BOARD_SIZE = 15
CELL_SIZE = 36
MARGIN = 30
STONE_RADIUS = 14

EMPTY = 0
BLACK = 1
WHITE = 2

DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]  # horiz/vert/diag/anti-diag

MODE_PVP = "pvp"  # two-player
MODE_AI = "ai"    # vs computer

DIFF_LOW = "low"
DIFF_MID = "mid"
DIFF_HIGH = "high"

DIFF_LABEL = {DIFF_LOW: "低", DIFF_MID: "中", DIFF_HIGH: "高"}
MODE_LABEL = {MODE_PVP: "双人", MODE_AI: "人机"}

AI_DELAY_MS = 350  # computer move delay, keep UI responsive

CENTER = (BOARD_SIZE // 2, BOARD_SIZE // 2)


@dataclass(frozen=True)
class Move:
    r: int
    c: int
    color: int


class GomokuApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gomoku 五子棋")

        # ---------------- UI: status + controls ----------------
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(root, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(10, 0))

        control = tk.Frame(root)
        control.pack(fill="x", padx=10, pady=8)

        self.btn_restart = tk.Button(control, text="重新开始", command=self.restart)
        self.btn_restart.pack(side="left")

        self.btn_undo = tk.Button(control, text="悔棋", command=self.undo)
        self.btn_undo.pack(side="left", padx=(8, 0))

        # Mode selection (PVP/AI)
        self.ui_mode = tk.StringVar(value=MODE_PVP)
        tk.Label(control, text="模式：").pack(side="left", padx=(18, 0))
        self.rb_pvp = tk.Radiobutton(control, text="双人", variable=self.ui_mode, value=MODE_PVP, command=self.on_mode_or_diff_changed)
        self.rb_ai = tk.Radiobutton(control, text="人机", variable=self.ui_mode, value=MODE_AI, command=self.on_mode_or_diff_changed)
        self.rb_pvp.pack(side="left")
        self.rb_ai.pack(side="left")

        # Difficulty selection (Low/Mid/High)
        self.ui_diff = tk.StringVar(value=DIFF_LOW)
        tk.Label(control, text="难度：").pack(side="left", padx=(18, 0))
        self.diff_menu = tk.OptionMenu(control, self.ui_diff, DIFF_LOW, DIFF_MID, DIFF_HIGH, command=lambda _: self.on_mode_or_diff_changed())
        self.diff_menu.pack(side="left")

        # ---------------- Canvas ----------------
        width = MARGIN * 2 + CELL_SIZE * (BOARD_SIZE - 1)
        height = MARGIN * 2 + CELL_SIZE * (BOARD_SIZE - 1)
        self.canvas = tk.Canvas(root, width=width, height=height, bg="#f2d08a", highlightthickness=0)
        self.canvas.pack(padx=10, pady=(0, 10))
        self.canvas.bind("<Button-1>", self.on_click)

        # keyboard shortcuts
        root.bind("<r>", lambda e: self.restart())
        root.bind("<u>", lambda e: self.undo())

        # runtime state
        self.ai_job = None
        self.pending_restart = False  # switch mode/diff -> require restart to apply

        self.restart()

    # ----------------------------
    # Game lifecycle
    # ----------------------------
    def restart(self):
        # Cancel scheduled AI move
        self.cancel_ai_job()

        # Apply selections on restart
        self.mode = self.ui_mode.get()
        self.difficulty = self.ui_diff.get()
        self.pending_restart = False

        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current = BLACK  # black always starts (human is black in AI mode)
        self.game_over = False
        self.ai_thinking = False

        self.moves: list[Move] = []
        self.redraw()
        self.update_controls_enabled()
        self.update_status()

    def on_mode_or_diff_changed(self):
        # Difficulty only meaningful in AI mode; still allow selecting but disable menu in PVP for clarity.
        self.pending_restart = True
        self.update_controls_enabled()
        self.update_status()

    def update_controls_enabled(self):
        # disable difficulty selection in PVP (optional UX)
        state = "normal" if self.ui_mode.get() == MODE_AI else "disabled"
        self.diff_menu.configure(state=state)

    # ----------------------------
    # UI / drawing
    # ----------------------------
    def redraw(self):
        self.canvas.delete("all")
        self.draw_grid()
        self.draw_stones()

    def draw_grid(self):
        # board lines
        for i in range(BOARD_SIZE):
            y = MARGIN + i * CELL_SIZE
            self.canvas.create_line(MARGIN, y, MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, y, fill="#333")
            x = MARGIN + i * CELL_SIZE
            self.canvas.create_line(x, MARGIN, x, MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, fill="#333")

        # star points
        star_points = [(3, 3), (3, 11), (11, 3), (11, 11), (7, 7)]
        for r, c in star_points:
            x, y = self.rc_to_xy(r, c)
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#111", outline="#111")

    def draw_stones(self):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = self.board[r][c]
                if color == EMPTY:
                    continue
                x, y = self.rc_to_xy(r, c)
                if color == BLACK:
                    fill, outline = "#111", "#111"
                else:
                    fill, outline = "#f7f7f7", "#333"

                self.canvas.create_oval(
                    x - STONE_RADIUS, y - STONE_RADIUS,
                    x + STONE_RADIUS, y + STONE_RADIUS,
                    fill=fill, outline=outline, width=2
                )

        # highlight last move
        if self.moves:
            last = self.moves[-1]
            x, y = self.rc_to_xy(last.r, last.c)
            self.canvas.create_rectangle(x - 7, y - 7, x + 7, y + 7, outline="#d10", width=2)

    def update_status(self):
        mode_eff = MODE_LABEL.get(self.mode, self.mode)
        diff_eff = DIFF_LABEL.get(self.difficulty, self.difficulty)
        who = "黑" if self.current == BLACK else "白"

        if self.pending_restart:
            pending_mode = MODE_LABEL.get(self.ui_mode.get(), self.ui_mode.get())
            pending_diff = DIFF_LABEL.get(self.ui_diff.get(), self.ui_diff.get())
            msg = f"已选择：模式={pending_mode}"
            if self.ui_mode.get() == MODE_AI:
                msg += f"，难度={pending_diff}"
            msg += "。切换需点击【重新开始】生效。"
            self.status_var.set(msg)
            return

        if self.game_over:
            self.status_var.set(f"游戏结束。当前模式={mode_eff}" + (f"，难度={diff_eff}" if self.mode == MODE_AI else "") +
                                "。可【重新开始】或【悔棋】。（快捷键：R 重新开始，U 悔棋）")
            return

        if self.mode == MODE_AI and self.ai_thinking:
            self.status_var.set(f"当前模式={mode_eff}，难度={diff_eff}。电脑思考中…（请稍候）")
            return

        extra = f"当前模式={mode_eff}" + (f"，难度={diff_eff}" if self.mode == MODE_AI else "")
        self.status_var.set(f"{extra}。轮到：{who} 落子。（快捷键：R 重新开始，U 悔棋）")

    # ----------------------------
    # Input handling
    # ----------------------------
    def on_click(self, event):
        if self.pending_restart:
            return
        if self.game_over or self.ai_thinking:
            return

        # In AI mode, human is always BLACK; forbid click if it's computer's turn.
        if self.mode == MODE_AI and self.current != BLACK:
            return

        r, c = self.xy_to_rc(event.x, event.y)
        if r is None or c is None:
            return
        if self.board[r][c] != EMPTY:
            return

        self.play_move(r, c, self.current)

        # win check
        if self.check_win(r, c, self.current):
            self.game_over = True
            self.redraw()
            self.update_status()
            winner = "黑" if self.current == BLACK else "白"
            messagebox.showinfo("胜负已定", f"{winner} 胜！")
            return

        # switch player
        self.current = WHITE if self.current == BLACK else BLACK
        self.redraw()
        self.update_status()

        # AI move
        if self.mode == MODE_AI and not self.game_over and self.current == WHITE:
            self.schedule_ai_move()

    def play_move(self, r, c, color):
        self.board[r][c] = color
        self.moves.append(Move(r, c, color))

    # ----------------------------
    # Undo
    # ----------------------------
    def undo(self):
        if self.pending_restart:
            return
        if not self.moves:
            return

        # Allow undo after game over
        if self.game_over:
            self.game_over = False

        self.cancel_ai_job()
        self.ai_thinking = False

        steps = 1
        # In AI mode, undo two moves by default (human+computer), if possible.
        if self.mode == MODE_AI:
            steps = 2

        for _ in range(steps):
            if not self.moves:
                break
            mv = self.moves.pop()
            self.board[mv.r][mv.c] = EMPTY

        # determine current player by moves parity (BLACK starts)
        self.current = BLACK if (len(self.moves) % 2 == 0) else WHITE

        self.redraw()
        self.update_status()

    # ----------------------------
    # Win check
    # ----------------------------
    def check_win(self, r, c, color) -> bool:
        for dr, dc in DIRECTIONS:
            count = 1
            count += self.count_one_direction(r, c, dr, dc, color)
            count += self.count_one_direction(r, c, -dr, -dc, color)
            if count >= 5:
                return True
        return False

    def count_one_direction(self, r, c, dr, dc, color) -> int:
        cnt = 0
        rr, cc = r + dr, c + dc
        while 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and self.board[rr][cc] == color:
            cnt += 1
            rr += dr
            cc += dc
        return cnt

    # ----------------------------
    # AI scheduling
    # ----------------------------
    def schedule_ai_move(self):
        self.cancel_ai_job()
        self.ai_thinking = True
        self.update_status()
        self.ai_job = self.root.after(AI_DELAY_MS, self.do_ai_move)

    def cancel_ai_job(self):
        if self.ai_job is not None:
            try:
                self.root.after_cancel(self.ai_job)
            except Exception:
                pass
            self.ai_job = None

    def do_ai_move(self):
        self.ai_job = None
        if self.pending_restart or self.game_over:
            self.ai_thinking = False
            self.update_status()
            return
        if self.mode != MODE_AI or self.current != WHITE:
            self.ai_thinking = False
            self.update_status()
            return

        r, c = self.ai_choose_move()
        if r is None:
            # no legal moves (shouldn't happen unless board full)
            self.ai_thinking = False
            self.update_status()
            return

        self.play_move(r, c, WHITE)

        if self.check_win(r, c, WHITE):
            self.game_over = True
            self.ai_thinking = False
            self.redraw()
            self.update_status()
            messagebox.showinfo("胜负已定", "电脑（白）胜！")
            return

        self.current = BLACK
        self.ai_thinking = False
        self.redraw()
        self.update_status()

    # ----------------------------
    # AI core
    # ----------------------------
    def ai_choose_move(self):
        candidates = self.get_candidates(radius=2)
        if not candidates:
            return None, None

        if self.difficulty == DIFF_LOW:
            return self.ai_low(candidates)
        if self.difficulty == DIFF_MID:
            return self.ai_mid(candidates)
        return self.ai_high(candidates)

    def get_candidates(self, radius=2):
        # If empty board, choose center as only candidate
        if not self.moves:
            return [CENTER]

        occupied = [(mv.r, mv.c) for mv in self.moves]
        cand = set()
        for r0, c0 in occupied:
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r, c = r0 + dr, c0 + dc
                    if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == EMPTY:
                        cand.add((r, c))
        return list(cand)

    def ai_low(self, candidates):
        # Prefer closer to center; then random within top slice
        def center_dist(p):
            return abs(p[0] - CENTER[0]) + abs(p[1] - CENTER[1])

        candidates_sorted = sorted(candidates, key=center_dist)
        top_k = max(6, len(candidates_sorted) // 3)
        pick_pool = candidates_sorted[:top_k]
        return random.choice(pick_pool)

    def ai_mid(self, candidates):
        # 1) immediate win for AI
        for r, c in candidates:
            if self.is_win_move(r, c, WHITE):
                return (r, c)

        # 2) immediate block: if human can win next, block it
        for r, c in candidates:
            if self.is_win_move(r, c, BLACK):
                return (r, c)

        # 3) scoring
        best = None
        best_score = -10**18
        for r, c in candidates:
            s_ai = self.score_move(r, c, WHITE)
            s_hu = self.score_move(r, c, BLACK)
            # Combine: strong offense + defense
            score = s_ai + int(0.9 * s_hu)
            # slight center bias
            score -= (abs(r - CENTER[0]) + abs(c - CENTER[1])) * 3
            if score > best_score:
                best_score = score
                best = (r, c)
        return best

    def ai_high(self, candidates):
        """
        High: Mid's rules + one-ply lookahead (avoid giving opponent strong response).
        Keep it fast: limit candidates by static score first.
        """
        # 1) immediate win
        for r, c in candidates:
            if self.is_win_move(r, c, WHITE):
                return (r, c)

        # 2) immediate block
        for r, c in candidates:
            if self.is_win_move(r, c, BLACK):
                return (r, c)

        # Pre-rank by static score (top M only)
        scored = []
        for r, c in candidates:
            s = self.score_move(r, c, WHITE) + int(0.8 * self.score_move(r, c, BLACK))
            s -= (abs(r - CENTER[0]) + abs(c - CENTER[1])) * 2
            scored.append((s, r, c))
        scored.sort(reverse=True)
        top_moves = scored[:min(20, len(scored))]

        best = None
        best_val = -10**18

        for _, r, c in top_moves:
            # simulate AI move
            self.board[r][c] = WHITE

            # if win, choose immediately (already checked, but keep safe)
            if self.check_win(r, c, WHITE):
                self.board[r][c] = EMPTY
                return (r, c)

            # opponent best response (one ply)
            opp_candidates = self.get_candidates(radius=2)
            opp_best = self.best_opponent_response(opp_candidates)

            # value: AI move score - opponent best threat
            val = self.score_move(r, c, WHITE) - int(1.05 * opp_best)

            # revert
            self.board[r][c] = EMPTY

            if val > best_val:
                best_val = val
                best = (r, c)

        return best if best else self.ai_mid(candidates)

    def best_opponent_response(self, opp_candidates):
        if not opp_candidates:
            return 0

        # if opponent can win immediately, threat is huge
        for rr, cc in opp_candidates:
            if self.is_win_move(rr, cc, BLACK):
                return 10**12

        # otherwise, take max of combined threat score
        best = 0
        # limit responses for speed
        ranked = []
        for rr, cc in opp_candidates:
            s = self.score_move(rr, cc, BLACK) + int(0.6 * self.score_move(rr, cc, WHITE))
            ranked.append((s, rr, cc))
        ranked.sort(reverse=True)
        for s, _, _ in ranked[:min(15, len(ranked))]:
            if s > best:
                best = s
        return best

    def is_win_move(self, r, c, color):
        if self.board[r][c] != EMPTY:
            return False
        self.board[r][c] = color
        win = self.check_win(r, c, color)
        self.board[r][c] = EMPTY
        return win

    # ----------------------------
    # Scoring
    # ----------------------------
    def score_move(self, r, c, color):
        """
        Heuristic scoring for a move at (r,c) for 'color'.
        Higher means better.
        """
        if self.board[r][c] != EMPTY:
            return -10**15

        total = 0
        # For each direction, evaluate the line pattern around this point
        for dr, dc in DIRECTIONS:
            count, open_ends = self.line_count_and_open_ends(r, c, dr, dc, color)
            total += self.pattern_score(count, open_ends)
        return total

    def line_count_and_open_ends(self, r, c, dr, dc, color):
        """
        Consider placing color at (r,c). Count contiguous stones in both directions
        and whether ends are open.
        """
        # forward
        cnt1 = 0
        rr, cc = r + dr, c + dc
        while 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and self.board[rr][cc] == color:
            cnt1 += 1
            rr += dr
            cc += dc
        end1_open = (0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and self.board[rr][cc] == EMPTY)

        # backward
        cnt2 = 0
        rr, cc = r - dr, c - dc
        while 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and self.board[rr][cc] == color:
            cnt2 += 1
            rr -= dr
            cc -= dc
        end2_open = (0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and self.board[rr][cc] == EMPTY)

        count = 1 + cnt1 + cnt2  # including current point
        open_ends = (1 if end1_open else 0) + (1 if end2_open else 0)
        return count, open_ends

    def pattern_score(self, count, open_ends):
        """
        Simple but effective pattern scoring.
        """
        if count >= 5:
            return 10**12

        # Open four / closed four
        if count == 4 and open_ends == 2:
            return 10**8
        if count == 4 and open_ends == 1:
            return 10**6

        # Open three / closed three
        if count == 3 and open_ends == 2:
            return 10**5
        if count == 3 and open_ends == 1:
            return 10**3

        # Two
        if count == 2 and open_ends == 2:
            return 500
        if count == 2 and open_ends == 1:
            return 80

        # One
        if count == 1 and open_ends == 2:
            return 10
        return 1

    # ----------------------------
    # Coordinate helpers
    # ----------------------------
    def rc_to_xy(self, r, c):
        x = MARGIN + c * CELL_SIZE
        y = MARGIN + r * CELL_SIZE
        return x, y

    def xy_to_rc(self, x, y):
        dx = x - MARGIN
        dy = y - MARGIN
        if dx < -CELL_SIZE / 2 or dy < -CELL_SIZE / 2:
            return None, None

        c = int(round(dx / CELL_SIZE))
        r = int(round(dy / CELL_SIZE))
        if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
            gx, gy = self.rc_to_xy(r, c)
            if abs(gx - x) <= CELL_SIZE / 2 and abs(gy - y) <= CELL_SIZE / 2:
                return r, c
        return None, None


def main():
    root = tk.Tk()
    app = GomokuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

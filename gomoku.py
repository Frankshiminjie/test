import tkinter as tk
from tkinter import messagebox


class GomokuApp:
    """Simple two-player Gomoku (Five in a Row) using tkinter."""

    BOARD_SIZE = 15
    CELL_SIZE = 30
    MARGIN = 20
    STONE_RADIUS = 12

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Gomoku")

        canvas_size = self.MARGIN * 2 + self.CELL_SIZE * (self.BOARD_SIZE - 1)
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_size,
            height=canvas_size,
            bg="#F0D9B5",
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.status_label = tk.Label(self.root, text="", anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w", padx=10)

        button_frame = tk.Frame(self.root)
        button_frame.grid(row=1, column=1, sticky="e", padx=10)
        tk.Button(button_frame, text="重新开始", command=self.reset_game).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(button_frame, text="悔棋", command=self.undo_move).pack(
            side=tk.LEFT
        )

        self.canvas.bind("<Button-1>", self.handle_click)

        self.board = []
        self.move_history = []
        self.current_player = "black"
        self.game_over = False

        self.reset_game()

    def reset_game(self) -> None:
        """Reset the game state and redraw the board."""
        self.board = [
            [None for _ in range(self.BOARD_SIZE)] for _ in range(self.BOARD_SIZE)
        ]
        self.move_history = []
        self.current_player = "black"
        self.game_over = False
        self.redraw_board()
        self.update_status("游戏进行中")

    def redraw_board(self) -> None:
        """Draw the grid lines and any existing stones."""
        self.canvas.delete("all")
        for i in range(self.BOARD_SIZE):
            x = self.MARGIN + i * self.CELL_SIZE
            y = self.MARGIN + i * self.CELL_SIZE
            self.canvas.create_line(
                self.MARGIN,
                y,
                self.MARGIN + self.CELL_SIZE * (self.BOARD_SIZE - 1),
                y,
            )
            self.canvas.create_line(
                x,
                self.MARGIN,
                x,
                self.MARGIN + self.CELL_SIZE * (self.BOARD_SIZE - 1),
            )

        for row in range(self.BOARD_SIZE):
            for col in range(self.BOARD_SIZE):
                if self.board[row][col]:
                    self.draw_stone(row, col, self.board[row][col])

    def draw_stone(self, row: int, col: int, color: str) -> None:
        """Draw a stone at a specific grid cell."""
        x = self.MARGIN + col * self.CELL_SIZE
        y = self.MARGIN + row * self.CELL_SIZE
        self.canvas.create_oval(
            x - self.STONE_RADIUS,
            y - self.STONE_RADIUS,
            x + self.STONE_RADIUS,
            y + self.STONE_RADIUS,
            fill=color,
            outline="black",
        )

    def handle_click(self, event: tk.Event) -> None:
        """Place a stone on the closest grid intersection."""
        if self.game_over:
            return

        col = int(round((event.x - self.MARGIN) / self.CELL_SIZE))
        row = int(round((event.y - self.MARGIN) / self.CELL_SIZE))

        if not (0 <= row < self.BOARD_SIZE and 0 <= col < self.BOARD_SIZE):
            return
        if self.board[row][col] is not None:
            return

        self.board[row][col] = self.current_player
        self.move_history.append((row, col, self.current_player))
        self.draw_stone(row, col, self.current_player)

        if self.check_win(row, col, self.current_player):
            self.game_over = True
            winner = "黑" if self.current_player == "black" else "白"
            self.update_status(f"{winner}方胜利")
            messagebox.showinfo("游戏结束", f"{winner}方胜利！")
            return

        self.current_player = "white" if self.current_player == "black" else "black"
        self.update_status("游戏进行中")

    def update_status(self, game_state: str) -> None:
        """Update the label showing the current player and game state."""
        player_text = "黑" if self.current_player == "black" else "白"
        self.status_label.config(text=f"当前回合：{player_text} | 状态：{game_state}")

    def undo_move(self) -> None:
        """Undo the last move if possible."""
        if self.game_over:
            return
        if not self.move_history:
            return

        last_row, last_col, last_player = self.move_history.pop()
        self.board[last_row][last_col] = None
        self.current_player = last_player
        self.redraw_board()
        self.update_status("游戏进行中")

    def check_win(self, row: int, col: int, color: str) -> bool:
        """Check whether the newly placed stone wins the game."""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for d_row, d_col in directions:
            count = 1
            count += self.count_in_direction(row, col, color, d_row, d_col)
            count += self.count_in_direction(row, col, color, -d_row, -d_col)
            if count >= 5:
                return True
        return False

    def count_in_direction(
        self, row: int, col: int, color: str, d_row: int, d_col: int
    ) -> int:
        """Count consecutive stones of the same color in one direction."""
        count = 0
        r = row + d_row
        c = col + d_col
        while 0 <= r < self.BOARD_SIZE and 0 <= c < self.BOARD_SIZE:
            if self.board[r][c] != color:
                break
            count += 1
            r += d_row
            c += d_col
        return count


if __name__ == "__main__":
    root = tk.Tk()
    app = GomokuApp(root)
    root.mainloop()

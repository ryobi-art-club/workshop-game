"""ブロック崩し (tkinter 版)

操作:
    ← / → または A / D : パドル移動（マウスでも操作可）
    スペース           : ボール発射 / 一時停止 / リトライ
    Esc                : 終了
"""

import math
import random
import tkinter as tk

# ---- 画面・ゲーム設定 ----
WIDTH, HEIGHT = 640, 480
FPS = 60
FRAME_MS = 1000 // FPS

PADDLE_W, PADDLE_H = 90, 12
PADDLE_Y = HEIGHT - 40
PADDLE_SPEED = 8

BALL_R = 7
BALL_SPEED = 5.0
BALL_SPEED_MAX = 9.0

BLOCK_ROWS, BLOCK_COLS = 6, 10
BLOCK_H = 20
BLOCK_GAP = 4
BLOCK_TOP = 60
ROW_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]

LIVES = 3
BG = "#1e1e2e"
FG = "#f5f5f5"


class Breakout:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("ブロック崩し")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.keys: set[str] = set()
        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym.lower()))
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", lambda e: self.on_action())

        self.new_game()
        self.loop()

    # ---- 初期化 ----
    def new_game(self) -> None:
        self.canvas.delete("all")
        self.score = 0
        self.lives = LIVES
        self.state = "ready"  # ready / playing / paused / over / clear

        self.paddle_x = (WIDTH - PADDLE_W) / 2
        self.paddle = self.canvas.create_rectangle(0, 0, 0, 0, fill=FG, outline="")
        self.ball = self.canvas.create_oval(0, 0, 0, 0, fill="#ffffff", outline="")

        self.blocks: dict[int, int] = {}  # canvas id -> 得点
        block_w = (WIDTH - BLOCK_GAP * (BLOCK_COLS + 1)) / BLOCK_COLS
        for r in range(BLOCK_ROWS):
            for c in range(BLOCK_COLS):
                x1 = BLOCK_GAP + c * (block_w + BLOCK_GAP)
                y1 = BLOCK_TOP + r * (BLOCK_H + BLOCK_GAP)
                bid = self.canvas.create_rectangle(
                    x1, y1, x1 + block_w, y1 + BLOCK_H, fill=ROW_COLORS[r], outline=""
                )
                self.blocks[bid] = (BLOCK_ROWS - r) * 10  # 上の段ほど高得点

        self.hud = self.canvas.create_text(10, 20, anchor="w", fill=FG, font=("Meiryo", 12))
        self.message = self.canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 60, fill=FG, font=("Meiryo", 16, "bold"), justify="center"
        )
        self.reset_ball()
        self.update_hud()

    def reset_ball(self) -> None:
        self.state = "ready"
        self.speed = BALL_SPEED
        self.vx, self.vy = 0.0, 0.0
        self.stick_ball_to_paddle()
        self.show_message("スペース / クリックで発射")

    def stick_ball_to_paddle(self) -> None:
        self.bx = self.paddle_x + PADDLE_W / 2
        self.by = PADDLE_Y - BALL_R - 1

    def launch(self) -> None:
        angle = math.radians(random.uniform(-60, -120))  # 上方向に少しランダム
        self.vx = self.speed * math.cos(angle)
        self.vy = self.speed * math.sin(angle)
        self.state = "playing"
        self.show_message("")

    # ---- 入力 ----
    def on_key_press(self, e: tk.Event) -> None:
        key = e.keysym.lower()
        self.keys.add(key)
        if key == "space":
            self.on_action()
        elif key == "escape":
            self.root.destroy()

    def on_action(self) -> None:
        if self.state == "ready":
            self.launch()
        elif self.state == "playing":
            self.state = "paused"
            self.show_message("一時停止中\nスペースで再開")
        elif self.state == "paused":
            self.state = "playing"
            self.show_message("")
        elif self.state in ("over", "clear"):
            self.new_game()

    def on_mouse_move(self, e: tk.Event) -> None:
        if self.state in ("ready", "playing"):
            self.paddle_x = min(max(e.x - PADDLE_W / 2, 0), WIDTH - PADDLE_W)

    # ---- メインループ ----
    def loop(self) -> None:
        if self.state in ("ready", "playing"):
            self.move_paddle()
            if self.state == "ready":
                self.stick_ball_to_paddle()
            else:
                self.move_ball()
        self.draw()
        self.root.after(FRAME_MS, self.loop)

    def move_paddle(self) -> None:
        dx = 0
        if self.keys & {"left", "a"}:
            dx -= PADDLE_SPEED
        if self.keys & {"right", "d"}:
            dx += PADDLE_SPEED
        self.paddle_x = min(max(self.paddle_x + dx, 0), WIDTH - PADDLE_W)

    def move_ball(self) -> None:
        # 高速時のすり抜け防止のため、1フレームを細かく分割して判定
        steps = max(1, int(self.speed // BALL_R) + 1)
        for _ in range(steps):
            self.bx += self.vx / steps
            self.by += self.vy / steps
            if self.check_collisions():
                return

    def check_collisions(self) -> bool:
        """衝突処理。ボールを失った・クリアした場合は True を返す。"""
        # 壁
        if self.bx - BALL_R <= 0:
            self.bx, self.vx = BALL_R, abs(self.vx)
        elif self.bx + BALL_R >= WIDTH:
            self.bx, self.vx = WIDTH - BALL_R, -abs(self.vx)
        if self.by - BALL_R <= 0:
            self.by, self.vy = BALL_R, abs(self.vy)

        # 落下
        if self.by - BALL_R > HEIGHT:
            self.lives -= 1
            self.update_hud()
            if self.lives <= 0:
                self.state = "over"
                self.show_message(f"GAME OVER\nスコア: {self.score}\nスペースでリトライ")
            else:
                self.reset_ball()
            return True

        # パドル: 当たった位置で反射角を変える
        if (
            self.vy > 0
            and PADDLE_Y <= self.by + BALL_R <= PADDLE_Y + PADDLE_H
            and self.paddle_x - BALL_R <= self.bx <= self.paddle_x + PADDLE_W + BALL_R
        ):
            offset = (self.bx - (self.paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)
            offset = max(-1.0, min(1.0, offset))
            angle = math.radians(-90 + offset * 60)
            self.vx = self.speed * math.cos(angle)
            self.vy = self.speed * math.sin(angle)
            self.by = PADDLE_Y - BALL_R

        # ブロック
        hits = self.canvas.find_overlapping(
            self.bx - BALL_R, self.by - BALL_R, self.bx + BALL_R, self.by + BALL_R
        )
        for bid in hits:
            if bid not in self.blocks:
                continue
            x1, y1, x2, y2 = self.canvas.coords(bid)
            # めり込み量が小さい軸で反射させる
            overlap_x = min(self.bx + BALL_R - x1, x2 - (self.bx - BALL_R))
            overlap_y = min(self.by + BALL_R - y1, y2 - (self.by - BALL_R))
            if overlap_x < overlap_y:
                self.vx = -self.vx
            else:
                self.vy = -self.vy

            self.score += self.blocks.pop(bid)
            self.canvas.delete(bid)
            self.speed_up()
            self.update_hud()

            if not self.blocks:
                self.state = "clear"
                self.show_message(f"CLEAR!\nスコア: {self.score}\nスペースでもう一度")
                return True
            break  # 1ステップにつき1ブロックだけ壊す
        return False

    def speed_up(self) -> None:
        self.speed = min(self.speed * 1.01, BALL_SPEED_MAX)
        norm = math.hypot(self.vx, self.vy)
        self.vx = self.vx / norm * self.speed
        self.vy = self.vy / norm * self.speed

    # ---- 描画 ----
    def draw(self) -> None:
        self.canvas.coords(
            self.paddle, self.paddle_x, PADDLE_Y, self.paddle_x + PADDLE_W, PADDLE_Y + PADDLE_H
        )
        self.canvas.coords(
            self.ball, self.bx - BALL_R, self.by - BALL_R, self.bx + BALL_R, self.by + BALL_R
        )

    def update_hud(self) -> None:
        self.canvas.itemconfigure(
            self.hud, text=f"スコア: {self.score}    残り: {'●' * self.lives}"
        )

    def show_message(self, text: str) -> None:
        self.canvas.itemconfigure(self.message, text=text)
        self.canvas.tag_raise(self.message)


def main() -> None:
    root = tk.Tk()
    Breakout(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""
Escape the Qubits
Student-friendly Pygame game:
- Grid-based board (start bottom-left, goal top-right)
- Qubit creatures randomly pop up in tiles and fade out
- Avoid qubits and reach the destination within a timer
"""

import pygame
import sys
import random
import time
import colorsys

# -------------------- Configuration --------------------
GRID_COLS = 10
GRID_ROWS = 10
TILE_SIZE = 64                 # pixels per tile
HUD_HEIGHT = 80                 # extra area for timer / text
SCREEN_WIDTH = GRID_COLS * TILE_SIZE
SCREEN_HEIGHT = GRID_ROWS * TILE_SIZE + HUD_HEIGHT

FPS = 60

TOTAL_TIME = 45.0               # seconds to reach the goal
MAX_ACTIVE_QUBITS = 6
SPAWN_INTERVAL_MIN = 0.4        # seconds between qubit spawns (min)
SPAWN_INTERVAL_MAX = 1.1        # seconds between qubit spawns (max)
QUBIT_LIFETIME = 1.2            # how long a qubit stays (seconds)

PLAYER_COLOR = (250, 250, 250)
DEST_COLOR = (255, 215, 0)

# -------------------------------------------------------

def hsv_to_rgb255(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


class Qubit:
    """A qubit creature that appears on a grid tile for a short time and fades out."""
    def __init__(self, grid_pos, spawn_time, lifetime=QUBIT_LIFETIME):
        self.grid_pos = grid_pos         # (col, row)
        self.spawn_time = spawn_time
        self.lifetime = lifetime

    def age(self, now):
        return now - self.spawn_time

    def is_alive(self, now):
        return self.age(now) < self.lifetime

    def alpha(self, now):
        """Return 0-255 alpha (fade out as age increases)."""
        a = self.age(now)
        frac = max(0.0, min(1.0, a / self.lifetime))
        # fade in a little then fade out: small ease
        # quick pop then fade
        return int(255 * (1.0 - frac))


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Escape the Qubits")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 54)

        # grid positions: player starts bottom-left
        self.start = (0, GRID_ROWS - 1)
        self.goal = (GRID_COLS - 1, 0)
        self.reset()

    def reset(self):
        self.player = list(self.start)
        self.qubits = []                 # list of Qubit
        self.start_time = time.time()
        self.next_spawn_time = self.start_time + random.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)
        self.running = True
        self.win = False
        self.lose = False
        self.pause = False

    def spawn_qubit(self, now):
        """Spawn a qubit on a random tile (can pop on player's tile -> instant lose).
           We never spawn on the goal tile to avoid unfair blocking."""
        if len(self.qubits) >= MAX_ACTIVE_QUBITS:
            return
        tries = 0
        while tries < 50:
            c = random.randrange(GRID_COLS)
            r = random.randrange(GRID_ROWS)
            if (c, r) == self.goal:
                tries += 1
                continue
            # allow spawn on player tile to make it challenging
            candidate = (c, r)
            # ensure no active qubit already at that tile
            if any(q.grid_pos == candidate and q.is_alive(now) for q in self.qubits):
                tries += 1
                continue
            self.qubits.append(Qubit(candidate, now))
            return

    def grid_to_pixel(self, grid_pos):
        col, row = grid_pos
        x = col * TILE_SIZE
        y = row * TILE_SIZE
        return x, y

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit(0)

                if self.win or self.lose:
                    if event.key == pygame.K_r:
                        self.reset()
                    continue

                # Movement keys
                if event.key == pygame.K_LEFT:
                    self.try_move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self.try_move(1, 0)
                elif event.key == pygame.K_UP:
                    self.try_move(0, -1)
                elif event.key == pygame.K_DOWN:
                    self.try_move(0, 1)

    def try_move(self, dx, dy):
        if not (self.running and not self.pause):
            return
        new_c = self.player[0] + dx
        new_r = self.player[1] + dy
        if 0 <= new_c < GRID_COLS and 0 <= new_r < GRID_ROWS:
            self.player = [new_c, new_r]
            now = time.time()
            # check collision with any alive qubit at new cell
            for q in self.qubits:
                if q.grid_pos == tuple(self.player) and q.is_alive(now):
                    self.lose = True
                    self.running = False
                    return
            # check if reached goal
            if tuple(self.player) == self.goal:
                self.win = True
                self.running = False
                return

    def update(self):
        now = time.time()

        # Spawn qubit if time
        if now >= self.next_spawn_time and self.running:
            self.spawn_qubit(now)
            self.next_spawn_time = now + random.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

        # Remove dead qubits
        self.qubits = [q for q in self.qubits if q.is_alive(now)]

        # If a qubit popped exactly on player's tile (spawned this frame), detect
        for q in self.qubits:
            if q.grid_pos == tuple(self.player) and q.is_alive(now) and self.running:
                # immediate lose
                self.lose = True
                self.running = False
                return

        # Timer check
        elapsed = now - self.start_time
        time_left = TOTAL_TIME - elapsed
        if time_left <= 0 and self.running:
            self.lose = True
            self.running = False

    def draw_grid(self):
        # colorful checkerboard using HSV
        for c in range(GRID_COLS):
            for r in range(GRID_ROWS):
                x = c * TILE_SIZE
                y = r * TILE_SIZE
                # compute a hue that varies across the board to look colorful
                hue = ((c / (GRID_COLS - 1) if GRID_COLS > 1 else 0) +
                       (r / (GRID_ROWS - 1) if GRID_ROWS > 1 else 0)) / 2.5
                color = hsv_to_rgb255((hue + 0.07) % 1.0, 0.55, 0.95)
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, color, rect)
                # subtle grid line
                pygame.draw.rect(self.screen, (200, 200, 200), rect, 1)

        # draw goal tile highlight
        gx, gy = self.grid_to_pixel(self.goal)
        goal_rect = pygame.Rect(gx, gy, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(self.screen, DEST_COLOR, goal_rect)
        pygame.draw.rect(self.screen, (120, 120, 0), goal_rect, 3)
        # small star in center
        cx = gx + TILE_SIZE // 2
        cy = gy + TILE_SIZE // 2
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 8)

    def draw_qubits(self):
        now = time.time()
        for q in self.qubits:
            if not q.is_alive(now):
                continue
            x, y = self.grid_to_pixel(q.grid_pos)
            cx = x + TILE_SIZE // 2
            cy = y + TILE_SIZE // 2
            # compute alpha and radius
            alpha = q.alpha(now)
            radius = int(TILE_SIZE * 0.36)
            # pick a color based on grid pos to vary look
            hue = ((q.grid_pos[0] + q.grid_pos[1]) / (GRID_COLS + GRID_ROWS)) % 1.0
            color_rgb = hsv_to_rgb255(hue, 0.8, 1.0)
            # draw with per-surface alpha
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            # outer glow
            glow_alpha = min(120, alpha // 2 + 60)
            pygame.draw.circle(surf, (color_rgb[0], color_rgb[1], color_rgb[2], glow_alpha), (radius, radius), radius)
            # inner core
            core_alpha = alpha
            pygame.draw.circle(surf, (255, 255, 255, core_alpha), (radius, radius), int(radius * 0.55))
            self.screen.blit(surf, (cx - radius, cy - radius))

    def draw_player(self):
        x, y = self.grid_to_pixel(tuple(self.player))
        cx = x + TILE_SIZE // 2
        cy = y + TILE_SIZE // 2
        radius = int(TILE_SIZE * 0.36)
        # player body
        pygame.draw.circle(self.screen, PLAYER_COLOR, (cx, cy), radius)
        # little eyes to look cute
        eye_offset = radius // 3
        pygame.draw.circle(self.screen, (60, 60, 60), (cx - eye_offset, cy - 6), 5)
        pygame.draw.circle(self.screen, (60, 60, 60), (cx + eye_offset, cy - 6), 5)
        # light ring
        pygame.draw.circle(self.screen, (200, 200, 255), (cx, cy), radius, 3)

    def draw_hud(self):
        now = time.time()
        elapsed = now - self.start_time
        time_left = max(0.0, TOTAL_TIME - elapsed)
        # Timer text
        txt = f"Time left: {int(time_left)}s"
        surf = self.font.render(txt, True, (20, 20, 20))
        self.screen.blit(surf, (10, SCREEN_HEIGHT - HUD_HEIGHT + 12))

        # Timer bar
        bar_x = 170
        bar_y = SCREEN_HEIGHT - HUD_HEIGHT + 18
        bar_w = SCREEN_WIDTH - bar_x - 20
        bar_h = 18
        frac = max(0.0, min(1.0, time_left / TOTAL_TIME))
        pygame.draw.rect(self.screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(self.screen, (60, 180, 60), (bar_x, bar_y, int(bar_w * frac), bar_h))
        pygame.draw.rect(self.screen, (0,0,0), (bar_x, bar_y, bar_w, bar_h), 2)

        # Instructions
        ins = "Use arrow keys to move. Avoid qubits! Reach the golden tile. R = restart."
        ins_surf = self.font.render(ins, True, (30, 30, 30))
        self.screen.blit(ins_surf, (10, SCREEN_HEIGHT - HUD_HEIGHT + 40))

    def draw_end_screen(self):
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2 - 30
        if self.win:
            text = "You Win! 🎉"
            sub = "Press R to play again"
            color = (40, 160, 40)
        else:
            text = "Game Over 💥"
            sub = "Press R to try again"
            color = (200, 40, 40)

        txt_surf = self.big_font.render(text, True, color)
        rect = txt_surf.get_rect(center=(center_x, center_y))
        self.screen.blit(txt_surf, rect)

        sub_surf = self.font.render(sub, True, (60, 60, 60))
        sub_rect = sub_surf.get_rect(center=(center_x, center_y + 60))
        self.screen.blit(sub_surf, sub_rect)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()
            if self.running:
                self.update()

            # Draw
            self.screen.fill((10, 10, 20))
            self.draw_grid()
            self.draw_qubits()
            self.draw_player()
            self.draw_hud()

            if not self.running:
                self.draw_end_screen()

            pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()

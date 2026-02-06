import math
import random
import sys
from dataclasses import dataclass

import pygame

WIDTH, HEIGHT = 900, 700
FPS = 60

PADDLE_WIDTH = 120
PADDLE_HEIGHT = 16
PADDLE_SPEED = 8

BALL_RADIUS = 8
BALL_SPEED = 6

BLOCK_WIDTH = 70
BLOCK_HEIGHT = 25
BLOCK_PADDING = 6
TOP_OFFSET = 80

POWERUP_SIZE = 18
POWERUP_SPEED = 3
POWERUP_DROP_CHANCE = 0.2

BACKGROUND = (20, 20, 30)
TEXT_COLOR = (240, 240, 250)

BLOCK_COLORS = [
    (237, 98, 98),
    (255, 183, 77),
    (255, 241, 118),
    (129, 199, 132),
    (79, 195, 247),
    (186, 104, 200),
]

LEVELS = [
    [
        "1111111111",
        "1222222221",
        "1233333321",
        "1222222221",
        "1111111111",
    ],
    [
        "1000000001",
        "0111111110",
        "0012222100",
        "0003330000",
        "0003330000",
        "0012222100",
        "0111111110",
        "1000000001",
    ],
    [
        "1111111111",
        "0000000000",
        "2222222222",
        "0000000000",
        "3333333333",
        "0000000000",
        "4444444444",
    ],
]


@dataclass
class Ball:
    position: pygame.Vector2
    velocity: pygame.Vector2


@dataclass
class PowerUp:
    position: pygame.Vector2


class Block:
    def __init__(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self.rect = rect
        self.color = color
        self.alive = True


class BlockBreaker:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Block Breaker")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 24)
        self.large_font = pygame.font.SysFont("arial", 46, bold=True)

        self.level_index = 0
        self.score = 0
        self.lives = 3

        self.paddle = pygame.Rect(
            (WIDTH - PADDLE_WIDTH) // 2,
            HEIGHT - 60,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )

        self.balls: list[Ball] = []
        self.powerups: list[PowerUp] = []
        self.blocks: list[Block] = []
        self.reset_balls()
        self.load_level(self.level_index)

    def reset_balls(self) -> None:
        self.balls = [
            Ball(
                position=pygame.Vector2(self.paddle.centerx, self.paddle.top - 30),
                velocity=pygame.Vector2(0, -BALL_SPEED).rotate(random.uniform(-20, 20)),
            )
        ]

    def load_level(self, index: int) -> None:
        self.blocks.clear()
        layout = LEVELS[index % len(LEVELS)]
        cols = max(len(row) for row in layout)
        total_width = cols * BLOCK_WIDTH + (cols - 1) * BLOCK_PADDING
        start_x = (WIDTH - total_width) // 2

        for row_index, row in enumerate(layout):
            for col_index, char in enumerate(row):
                if char == "0":
                    continue
                color_index = (int(char) - 1) % len(BLOCK_COLORS)
                color = BLOCK_COLORS[color_index]
                x = start_x + col_index * (BLOCK_WIDTH + BLOCK_PADDING)
                y = TOP_OFFSET + row_index * (BLOCK_HEIGHT + BLOCK_PADDING)
                rect = pygame.Rect(x, y, BLOCK_WIDTH, BLOCK_HEIGHT)
                self.blocks.append(Block(rect, color))

    def spawn_powerup(self, block: Block) -> None:
        if random.random() < POWERUP_DROP_CHANCE:
            self.powerups.append(
                PowerUp(position=pygame.Vector2(block.rect.centerx, block.rect.centery))
            )

    def split_ball(self, ball: Ball) -> None:
        angle = random.uniform(20, 45)
        for direction in (-1, 1):
            new_velocity = ball.velocity.rotate(angle * direction)
            if new_velocity.length() == 0:
                new_velocity = pygame.Vector2(0, -BALL_SPEED)
            new_velocity = new_velocity.normalize() * BALL_SPEED
            self.balls.append(
                Ball(position=ball.position.copy(), velocity=new_velocity)
            )

    def handle_collisions(self) -> None:
        for ball in list(self.balls):
            ball_rect = pygame.Rect(
                ball.position.x - BALL_RADIUS,
                ball.position.y - BALL_RADIUS,
                BALL_RADIUS * 2,
                BALL_RADIUS * 2,
            )

            if ball_rect.colliderect(self.paddle):
                offset = (ball.position.x - self.paddle.centerx) / (PADDLE_WIDTH / 2)
                bounce_angle = offset * 60
                speed = max(ball.velocity.length(), BALL_SPEED)
                ball.velocity = pygame.Vector2(0, -1).rotate(bounce_angle) * speed
                ball.position.y = self.paddle.top - BALL_RADIUS

            for block in self.blocks:
                if not block.alive:
                    continue
                if ball_rect.colliderect(block.rect):
                    overlap_left = ball_rect.right - block.rect.left
                    overlap_right = block.rect.right - ball_rect.left
                    overlap_top = ball_rect.bottom - block.rect.top
                    overlap_bottom = block.rect.bottom - ball_rect.top
                    min_overlap = min(
                        overlap_left, overlap_right, overlap_top, overlap_bottom
                    )

                    if min_overlap == overlap_left:
                        ball.velocity.x = -abs(ball.velocity.x)
                    elif min_overlap == overlap_right:
                        ball.velocity.x = abs(ball.velocity.x)
                    elif min_overlap == overlap_top:
                        ball.velocity.y = -abs(ball.velocity.y)
                    else:
                        ball.velocity.y = abs(ball.velocity.y)

                    block.alive = False
                    self.score += 100
                    self.spawn_powerup(block)
                    break

        self.blocks = [block for block in self.blocks if block.alive]

    def update_powerups(self) -> None:
        for powerup in list(self.powerups):
            powerup.position.y += POWERUP_SPEED
            powerup_rect = pygame.Rect(
                powerup.position.x - POWERUP_SIZE // 2,
                powerup.position.y - POWERUP_SIZE // 2,
                POWERUP_SIZE,
                POWERUP_SIZE,
            )
            if powerup_rect.colliderect(self.paddle):
                if self.balls:
                    self.split_ball(self.balls[0])
                self.powerups.remove(powerup)
            elif powerup.position.y > HEIGHT + POWERUP_SIZE:
                self.powerups.remove(powerup)

    def update_balls(self) -> None:
        for ball in list(self.balls):
            ball.position += ball.velocity

            if ball.position.x <= BALL_RADIUS:
                ball.position.x = BALL_RADIUS
                ball.velocity.x = abs(ball.velocity.x)
            if ball.position.x >= WIDTH - BALL_RADIUS:
                ball.position.x = WIDTH - BALL_RADIUS
                ball.velocity.x = -abs(ball.velocity.x)
            if ball.position.y <= BALL_RADIUS:
                ball.position.y = BALL_RADIUS
                ball.velocity.y = abs(ball.velocity.y)

            if ball.position.y > HEIGHT + BALL_RADIUS:
                self.balls.remove(ball)

        if not self.balls:
            self.lives -= 1
            if self.lives > 0:
                self.reset_balls()

    def advance_level(self) -> None:
        if not self.blocks:
            self.level_index += 1
            self.load_level(self.level_index)
            self.reset_balls()

    def draw_hud(self) -> None:
        score_text = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        lives_text = self.font.render(f"Lives: {self.lives}", True, TEXT_COLOR)
        level_text = self.font.render(
            f"Level: {self.level_index + 1}", True, TEXT_COLOR
        )
        self.screen.blit(score_text, (20, 20))
        self.screen.blit(lives_text, (20, 50))
        self.screen.blit(level_text, (WIDTH - 140, 20))

    def draw(self) -> None:
        self.screen.fill(BACKGROUND)

        for block in self.blocks:
            pygame.draw.rect(self.screen, block.color, block.rect, border_radius=4)
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                block.rect,
                width=1,
                border_radius=4,
            )

        pygame.draw.rect(self.screen, (200, 200, 230), self.paddle, border_radius=6)

        for ball in self.balls:
            pygame.draw.circle(
                self.screen, (255, 255, 255), ball.position, BALL_RADIUS
            )
            pygame.draw.circle(
                self.screen, (135, 206, 250), ball.position, BALL_RADIUS - 2
            )

        for powerup in self.powerups:
            pygame.draw.rect(
                self.screen,
                (255, 215, 0),
                pygame.Rect(
                    powerup.position.x - POWERUP_SIZE // 2,
                    powerup.position.y - POWERUP_SIZE // 2,
                    POWERUP_SIZE,
                    POWERUP_SIZE,
                ),
                border_radius=4,
            )
            pygame.draw.circle(
                self.screen,
                (255, 255, 255),
                powerup.position,
                POWERUP_SIZE // 4,
            )

        self.draw_hud()
        pygame.display.flip()

    def show_game_over(self) -> None:
        self.screen.fill(BACKGROUND)
        text = self.large_font.render("Game Over", True, TEXT_COLOR)
        sub = self.font.render("Press R to restart or Q to quit", True, TEXT_COLOR)
        self.screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))
        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                    running = False

            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.paddle.x -= PADDLE_SPEED
            if keys[pygame.K_RIGHT]:
                self.paddle.x += PADDLE_SPEED
            self.paddle.x = max(0, min(WIDTH - PADDLE_WIDTH, self.paddle.x))

            if self.lives <= 0:
                self.show_game_over()
                if keys[pygame.K_r]:
                    self.level_index = 0
                    self.score = 0
                    self.lives = 3
                    self.powerups.clear()
                    self.load_level(self.level_index)
                    self.reset_balls()
                continue

            self.update_balls()
            self.handle_collisions()
            self.update_powerups()
            self.advance_level()
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    BlockBreaker().run()

import pygame
import sys
import math
import time
from enum import Enum
from typing import List, Tuple, Optional

# Game configuration
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
FPS = 60

# Colors
BACKGROUND_COLOR = (240, 235, 210)
BOARD_COLOR = (139, 90, 43)
STONE_COLOR = (105, 105, 105)
QUAN_COLOR = (218, 165, 32)
TEXT_COLOR = (70, 35, 10)
HIGHLIGHT_COLOR = (255, 215, 0)
PLAYER1_COLOR = (34, 139, 34)
PLAYER2_COLOR = (220, 20, 60)
ANIMATION_COLOR = (255, 50, 50)
VALID_MOVE_COLOR = (180, 140, 100)
DIRECTION_COLOR = (255, 255, 255)
ARROW_COLOR = (70, 35, 10)

class GameMode(Enum):
    HUMAN_VS_HUMAN = 1
    HUMAN_VS_AI = 2

class Player(Enum):
    PLAYER1 = 0
    PLAYER2 = 1

class Direction(Enum):
    CLOCKWISE = 1
    COUNTER_CLOCKWISE = -1

class AnimationState:
    def __init__(self):
        self.is_animating = False
        self.current_stones = 0
        self.current_position = 0
        self.animation_speed = 25
        self.frame_count = 0
        self.callback = None
        self.direction = Direction.CLOCKWISE
        
        # Capture animation
        self.capturing = False
        self.capture_positions = []
        self.capture_frame = 0
        self.capture_speed = 8
        
        # Hand animation - IMPROVED
        self.hand_visible = False
        self.hand_position = None
        self.hand_target = None
        self.hand_frame = 0
        self.captured_stones = 0
        self.hand_state = "reaching"
        
        # Sowing animation - NEW
        self.sowing_visible = False
        self.sowing_position = None
        self.sowing_frame = 0
        self.sowing_stones = []
        
        # Score effect
        self.score_effect = False
        self.score_effect_frame = 0
        self.score_effect_player = None

class GameState:
    def __init__(self):
        self.board = [0, 5, 5, 5, 5, 5, 10, 5, 5, 5, 5, 5, 10]
        self.current_player = Player.PLAYER1
        self.player1_score = 0
        self.player2_score = 0
        self.game_over = False
        self.winner = None
        self.move_count = 0

    def copy(self):
        new_state = GameState()
        new_state.board = self.board.copy()
        new_state.current_player = self.current_player
        new_state.player1_score = self.player1_score
        new_state.player2_score = self.player2_score
        new_state.game_over = self.game_over
        new_state.winner = self.winner
        new_state.move_count = self.move_count
        return new_state

    def get_valid_moves(self) -> List[int]:
        moves = []
        if self.current_player == Player.PLAYER1:
            for i in range(7, 12):
                if self.board[i] > 0:
                    moves.append(i)
        else:
            for i in range(1, 6):
                if self.board[i] > 0:
                    moves.append(i)
        
        if not moves:
            if (self.current_player == Player.PLAYER1 and self.player1_score >= 5) or \
               (self.current_player == Player.PLAYER2 and self.player2_score >= 5):
                if self.current_player == Player.PLAYER1:
                    moves = list(range(7, 12))
                else:
                    moves = list(range(1, 6))
        
        return moves

    def make_move_instant(self, position: int, direction: Direction) -> bool:
        if position not in self.get_valid_moves():
            return False
        
        if self.board[position] == 0:
            self._redistribute_stones()
            return True
        
        current_pos = position
        stones = self.board[position]
        self.board[position] = 0
        
        while stones > 0:
            while stones > 0:
                current_pos = self._next_position(current_pos, direction)
                self.board[current_pos] += 1
                stones -= 1
            
            next_pos = self._next_position(current_pos, direction)
            
            if next_pos == 6 or next_pos == 12:
                break
            
            if self.board[next_pos] > 0:
                stones = self.board[next_pos]
                self.board[next_pos] = 0
                current_pos = next_pos
            else:
                self._capture_stones_correct(current_pos, direction)
                break
        
        self._check_game_over()
        
        if not self.game_over:
            self.current_player = Player.PLAYER2 if self.current_player == Player.PLAYER1 else Player.PLAYER1
        
        self.move_count += 1
        return True

    def _next_position(self, pos: int, direction: Direction) -> int:
        if direction == Direction.CLOCKWISE:
            next_pos = (pos + 1) % 13
            if next_pos == 0:
                next_pos = 1
        else:
            next_pos = (pos - 1) % 13
            if next_pos == 0:
                next_pos = 12
        return next_pos

    def _capture_stones_correct(self, last_position: int, direction: Direction) -> List[int]:
        current_pos = last_position
        capture_positions = []
        
        while True:
            next_pos = self._next_position(current_pos, direction)
            
            if self.board[next_pos] == 0:
                capture_pos = self._next_position(next_pos, direction)
                
                # FIXED: Allow capturing quan (index 6 and 12) when they have stones
                if self.board[capture_pos] > 0:
                    capture_positions.append(capture_pos)
                    current_pos = capture_pos
                else:
                    break
            else:
                break
        
        return capture_positions

    def _redistribute_stones(self):
        if self.current_player == Player.PLAYER1 and self.player1_score >= 5:
            self.player1_score -= 5
            for i in range(7, 12):
                self.board[i] = 1
        elif self.current_player == Player.PLAYER2 and self.player2_score >= 5:
            self.player2_score -= 5
            for i in range(1, 6):
                self.board[i] = 1

    def _check_game_over(self):
        # Game ends when both quan are captured (have 0 stones)
        if self.board[6] == 0 and self.board[12] == 0:
            self.game_over = True
            # Collect remaining stones for each player
            for i in range(1, 6):  # Player 2's cells
                self.player2_score += self.board[i]
                self.board[i] = 0
            for i in range(7, 12):  # Player 1's cells
                self.player1_score += self.board[i]
                self.board[i] = 0
            
            # Determine winner
            if self.player1_score > self.player2_score:
                self.winner = Player.PLAYER1
            elif self.player2_score > self.player1_score:
                self.winner = Player.PLAYER2
            else:
                self.winner = None
        # Alternative game end: one side has no moves and can't redistribute
        elif not self.get_valid_moves():
            if self.current_player == Player.PLAYER1 and self.player1_score < 5:
                self.game_over = True
                self.winner = Player.PLAYER2
            elif self.current_player == Player.PLAYER2 and self.player2_score < 5:
                self.game_over = True
                self.winner = Player.PLAYER1

class AIEngine:
    def __init__(self, max_depth: int = 4):
        self.max_depth = max_depth
        self.nodes_evaluated = 0

    def get_best_move(self, state: GameState) -> Tuple[int, Direction]:
        self.nodes_evaluated = 0
        _, best_move, best_direction = self.minimax(state, self.max_depth, float('-inf'), float('inf'), True)
        print(f"AI evaluated {self.nodes_evaluated} nodes")
        return best_move, best_direction

    def minimax(self, state: GameState, depth: int, alpha: float, beta: float, maximizing: bool) -> Tuple[float, Optional[int], Direction]:
        self.nodes_evaluated += 1
        
        if depth == 0 or state.game_over:
            return self.evaluate_state(state), None, Direction.CLOCKWISE
        
        valid_moves = state.get_valid_moves()
        if not valid_moves:
            return self.evaluate_state(state), None, Direction.CLOCKWISE
        
        best_move = valid_moves[0]
        best_direction = Direction.CLOCKWISE
        
        if maximizing:
            max_eval = float('-inf')
            for move in valid_moves:
                for direction in [Direction.CLOCKWISE, Direction.COUNTER_CLOCKWISE]:
                    new_state = state.copy()
                    new_state.make_move_instant(move, direction)
                    eval_score, _, _ = self.minimax(new_state, depth - 1, alpha, beta, False)
                    
                    if eval_score > max_eval:
                        max_eval = eval_score
                        best_move = move
                        best_direction = direction
                    
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break
                if beta <= alpha:
                    break
            
            return max_eval, best_move, best_direction
        else:
            min_eval = float('inf')
            for move in valid_moves:
                for direction in [Direction.CLOCKWISE, Direction.COUNTER_CLOCKWISE]:
                    new_state = state.copy()
                    new_state.make_move_instant(move, direction)
                    eval_score, _, _ = self.minimax(new_state, depth - 1, alpha, beta, True)
                    
                    if eval_score < min_eval:
                        min_eval = eval_score
                        best_move = move
                        best_direction = direction
                    
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        break
                if beta <= alpha:
                    break
            
            return min_eval, best_move, best_direction

    def evaluate_state(self, state: GameState) -> float:
        if state.game_over:
            if state.winner == Player.PLAYER2:
                return 1000
            elif state.winner == Player.PLAYER1:
                return -1000
            else:
                return 0
        
        score_diff = state.player2_score - state.player1_score
        p2_stones = sum(state.board[1:6])
        p1_stones = sum(state.board[7:12])
        position_value = (p2_stones - p1_stones) * 0.2
        quan_safety = (state.board[6] + state.board[12]) * 5
        
        return score_diff + position_value + quan_safety

class OAnQuanGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("O An Quan - Vietnamese Traditional Game")
        self.clock = pygame.time.Clock()
        
        self.init_fonts()
        
        self.game_state = GameState()
        self.ai_engine = AIEngine(max_depth=4)
        self.game_mode = GameMode.HUMAN_VS_HUMAN
        self.selected_cell = None
        self.waiting_for_direction = False
        self.showing_direction_choice = False
        self.animation = AnimationState()
        
        self.in_menu = True
        self.cell_positions = {}
        self.setup_cell_positions()

    def init_fonts(self):
        try:
            self.title_font = pygame.font.Font(None, 48)
            self.font = pygame.font.Font(None, 28)
            self.small_font = pygame.font.Font(None, 20)
        except:
            self.title_font = pygame.font.SysFont('Arial', 48, bold=True)
            self.font = pygame.font.SysFont('Arial', 28, bold=True)
            self.small_font = pygame.font.SysFont('Arial', 20)

    def setup_cell_positions(self):
        cell_width, cell_height = 120, 90
        start_x, start_y = 180, 250
        
        self.cell_positions[6] = (70, start_y + cell_height//2 + 50)
        self.cell_positions[12] = (WINDOW_WIDTH - 130, start_y + cell_height//2 + 50)
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            self.cell_positions[5-i] = (x + cell_width//2, y + cell_height//2)
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            self.cell_positions[7+i] = (x + cell_width//2, y + cell_height//2)

    def check_auto_redistribute(self):
        valid_moves = self.game_state.get_valid_moves()
        
        if not valid_moves and not self.game_state.game_over:
            if self.game_state.current_player == Player.PLAYER1 and self.game_state.player1_score >= 5:
                self.game_state._redistribute_stones()
                return True
            elif self.game_state.current_player == Player.PLAYER2 and self.game_state.player2_score >= 5:
                self.game_state._redistribute_stones()
                return True
        return False

    def start_animation(self, start_pos: int, direction: Direction, callback=None):
        self.animation.is_animating = True
        self.animation.current_stones = self.game_state.board[start_pos]
        self.animation.current_position = start_pos
        self.animation.frame_count = 0
        self.animation.callback = callback
        self.animation.direction = direction
        
        self.start_sowing_animation(start_pos)
        self.game_state.board[start_pos] = 0

    def start_sowing_animation(self, start_pos):
        if start_pos in self.cell_positions:
            self.animation.sowing_visible = True
            self.animation.sowing_position = list(self.cell_positions[start_pos])
            self.animation.sowing_frame = 0
            self.animation.sowing_stones = []

    def update_animation(self):
        if self.animation.capturing:
            self.update_capture_animation()
            
        self.update_hand_animation()
        self.update_score_effect()
        self.update_sowing_animation()
            
        if not self.animation.is_animating:
            return
        
        self.animation.frame_count += 1
        
        if self.animation.frame_count >= self.animation.animation_speed:
            self.animation.frame_count = 0
            
            if self.animation.current_stones > 0:
                self.animation.current_position = self.game_state._next_position(
                    self.animation.current_position, self.animation.direction
                )
                
                self.game_state.board[self.animation.current_position] += 1
                self.animation.current_stones -= 1
                
                if self.animation.current_position in self.cell_positions:
                    self.animation.sowing_position = list(self.cell_positions[self.animation.current_position])
            else:
                next_pos = self.game_state._next_position(
                    self.animation.current_position, self.animation.direction
                )
                
                if next_pos == 6 or next_pos == 12:
                    self.animation.is_animating = False
                    self.animation.sowing_visible = False
                    if self.animation.callback:
                        self.animation.callback(self.animation.current_position)
                elif self.game_state.board[next_pos] > 0:
                    self.animation.current_stones = self.game_state.board[next_pos]
                    self.game_state.board[next_pos] = 0
                    self.animation.current_position = next_pos
                else:
                    self.animation.is_animating = False
                    self.animation.sowing_visible = False
                    if self.animation.callback:
                        self.animation.callback(self.animation.current_position)

    def update_sowing_animation(self):
        if not self.animation.sowing_visible:
            return
            
        self.animation.sowing_frame += 1
        
        if self.animation.sowing_frame % 10 == 0:
            self.animation.sowing_stones.append({
                'pos': list(self.animation.sowing_position),
                'life': 20
            })
        
        for stone in self.animation.sowing_stones[:]:
            stone['life'] -= 1
            if stone['life'] <= 0:
                self.animation.sowing_stones.remove(stone)

    def update_capture_animation(self):
        self.animation.capture_frame += 1
        
        if self.animation.capture_frame >= self.animation.capture_speed:
            self.animation.capture_frame = 0
            
            if self.animation.capture_positions:
                pos = self.animation.capture_positions.pop(0)
                captured = self.game_state.board[pos]
                self.game_state.board[pos] = 0
                
                self.start_hand_animation(pos, captured)
                
                if self.game_state.current_player == Player.PLAYER1:
                    self.game_state.player1_score += captured
                else:
                    self.game_state.player2_score += captured
                
                self.animation.score_effect = True
                self.animation.score_effect_frame = 0
                self.animation.score_effect_player = self.game_state.current_player
                
            else:
                self.animation.capturing = False
                if self.animation.callback:
                    self.animation.callback(None)

    def start_hand_animation(self, from_pos, stones):
        if from_pos in self.cell_positions:
            self.animation.hand_visible = True
            self.animation.hand_position = list(self.cell_positions[from_pos])
            self.animation.captured_stones = stones
            self.animation.hand_frame = 0
            self.animation.hand_state = "reaching"
            
            if self.game_state.current_player == Player.PLAYER1:
                self.animation.hand_target = [130, 120]
            else:
                self.animation.hand_target = [WINDOW_WIDTH - 150, 120]

    def update_hand_animation(self):
        if not self.animation.hand_visible:
            return
            
        self.animation.hand_frame += 1
        
        if self.animation.hand_state == "reaching":
            if self.animation.hand_frame < 10:
                self.animation.hand_position[1] += 2
            else:
                self.animation.hand_state = "grabbing"
                self.animation.hand_frame = 0
                
        elif self.animation.hand_state == "grabbing":
            if self.animation.hand_frame < 8:
                shake = 2 * math.sin(self.animation.hand_frame * 2)
                self.animation.hand_position[0] += shake
            else:
                self.animation.hand_state = "moving"
                self.animation.hand_frame = 0
                
        elif self.animation.hand_state == "moving":
            if self.animation.hand_frame < 30:
                progress = self.animation.hand_frame / 30
                start_x, start_y = self.cell_positions[list(self.cell_positions.keys())[0]]
                target_x, target_y = self.animation.hand_target
                
                current_x = start_x + (target_x - start_x) * progress
                current_y = start_y + (target_y - start_y) * progress
                
                self.animation.hand_position = [current_x, current_y]
            else:
                self.animation.hand_state = "releasing"
                self.animation.hand_frame = 0
                
        elif self.animation.hand_state == "releasing":
            if self.animation.hand_frame < 10:
                self.animation.hand_position[1] -= 1
            else:
                self.animation.hand_visible = False
            
    def update_score_effect(self):
        if self.animation.score_effect:
            self.animation.score_effect_frame += 1
            if self.animation.score_effect_frame > 20:
                self.animation.score_effect = False

    def start_capture_animation(self, positions, callback=None):
        if not positions:
            if callback:
                callback(None)
            return
            
        self.animation.capturing = True
        self.animation.capture_positions = positions.copy()
        self.animation.capture_frame = 0
        self.animation.callback = callback

    def draw_gradient_background(self):
        for y in range(WINDOW_HEIGHT):
            ratio = y / WINDOW_HEIGHT
            r = int(240 * (1 - ratio) + 220 * ratio)
            g = int(235 * (1 - ratio) + 210 * ratio)
            b = int(210 * (1 - ratio) + 180 * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (WINDOW_WIDTH, y))

    def draw_stone_3d(self, surface, x, y, is_quan=False, is_moving=False, is_capturing=False, size_factor=1.0):
        if is_quan:
            radius = int(12 * size_factor)
            color = QUAN_COLOR
        else:
            radius = int(8 * size_factor)
            color = STONE_COLOR
        
        if is_moving:
            color = ANIMATION_COLOR
            radius += 2
        elif is_capturing:
            color = (255, 100, 100)
            radius += 1
        
        pygame.draw.circle(surface, (0, 0, 0), (x + 2, y + 2), radius)
        pygame.draw.circle(surface, color, (x, y), radius)
        
        highlight_color = (min(255, color[0] + 60), min(255, color[1] + 60), min(255, color[2] + 60))
        pygame.draw.circle(surface, highlight_color, (x - radius//3, y - radius//3), max(1, radius//3))

    def draw_sowing_hand(self, surface, x, y):
        if not self.animation.sowing_visible:
            return
            
        hand_points = [
            (x - 8, y - 12), (x - 4, y - 15), (x, y - 14),
            (x + 4, y - 15), (x + 8, y - 12), (x + 6, y - 4),
            (x + 2, y + 2), (x - 2, y + 2), (x - 6, y - 4)
        ]
        
        shadow_points = [(px + 1, py + 1) for px, py in hand_points]
        pygame.draw.polygon(surface, (100, 100, 100), shadow_points)
        
        pygame.draw.polygon(surface, (255, 220, 177), hand_points)
        pygame.draw.polygon(surface, (200, 180, 140), hand_points, 2)
        
        for stone in self.animation.sowing_stones:
            alpha = int(255 * stone['life'] / 20)
            stone_surface = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(stone_surface, (*STONE_COLOR, alpha), (4, 4), 3)
            surface.blit(stone_surface, (stone['pos'][0] - 4, stone['pos'][1] - 4))

    def draw_hand_effect(self, surface, x, y, stones=0):
        if not self.animation.hand_visible:
            return
            
        hand_points = [
            (x - 15, y - 20), (x - 8, y - 25), (x, y - 23),
            (x + 8, y - 25), (x + 15, y - 20), (x + 12, y - 8),
            (x + 8, y), (x - 8, y), (x - 12, y - 8)
        ]
        
        shadow_points = [(px + 2, py + 2) for px, py in hand_points]
        pygame.draw.polygon(surface, (100, 100, 100), shadow_points)
        
        pygame.draw.polygon(surface, (255, 220, 177), hand_points)
        pygame.draw.polygon(surface, (200, 180, 140), hand_points, 2)
        
        finger_positions = [(x-10, y-18), (x-4, y-21), (x+4, y-21), (x+10, y-18)]
        for i, (fx, fy) in enumerate(finger_positions):
            finger_length = 8 if self.animation.hand_state == "grabbing" else 6
            pygame.draw.circle(surface, (240, 200, 160), (fx, fy), 4)
            pygame.draw.circle(surface, (200, 180, 140), (fx, fy), 4, 1)
            
            tip_y = fy - finger_length if self.animation.hand_state == "grabbing" else fy - 4
            pygame.draw.circle(surface, (220, 180, 140), (fx, tip_y), 2)
        
        if stones > 0:
            rows = min(3, (stones + 4) // 5)
            for i in range(min(stones, 15)):
                row = i // 5
                col = i % 5
                stone_x = x - 10 + col * 4
                stone_y = y - 3 + row * 4
                pygame.draw.circle(surface, STONE_COLOR, (stone_x, stone_y), 3)
                pygame.draw.circle(surface, (150, 150, 150), (stone_x, stone_y), 3, 1)
            
            if stones > 15:
                count_text = pygame.font.Font(None, 14).render(f"+{stones-15}", True, TEXT_COLOR)
                surface.blit(count_text, (x - 8, y + 8))

    def draw_flying_stones(self, surface):
        if self.animation.hand_visible and self.animation.captured_stones > 0:
            x, y = self.animation.hand_position
            
            stone_count = min(self.animation.captured_stones, 8)
            for i in range(stone_count):
                angle = i * 2 * math.pi / stone_count
                radius = 20 + 5 * math.sin(self.animation.hand_frame * 0.3)
                stone_x = x + radius * math.cos(angle)
                stone_y = y + radius * math.sin(angle)
                
                stone_surface = pygame.Surface((8, 8), pygame.SRCALPHA)
                alpha = 120 + 60 * math.sin(self.animation.hand_frame * 0.2 + i)
                pygame.draw.circle(stone_surface, (*STONE_COLOR, int(alpha)), (4, 4), 3)
                pygame.draw.circle(stone_surface, (255, 255, 255, 80), (2, 2), 1)
                surface.blit(stone_surface, (stone_x - 4, stone_y - 4))

    def draw_menu(self):
        self.draw_gradient_background()
        
        title_text = "O AN QUAN"
        title_surface = self.title_font.render(title_text, True, TEXT_COLOR)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH//2, 120))
        self.screen.blit(title_surface, title_rect)
        
        subtitle_text = "Vietnamese Traditional Game"
        subtitle_surface = self.small_font.render(subtitle_text, True, TEXT_COLOR)
        subtitle_rect = subtitle_surface.get_rect(center=(WINDOW_WIDTH//2, 170))
        self.screen.blit(subtitle_surface, subtitle_rect)
        
        button_width, button_height = 300, 70
        hvh_rect = pygame.Rect(WINDOW_WIDTH//2 - button_width//2, 250, button_width, button_height)
        hva_rect = pygame.Rect(WINDOW_WIDTH//2 - button_width//2, 350, button_width, button_height)
        
        self.draw_button(hvh_rect, "Human vs Human", PLAYER1_COLOR)
        self.draw_button(hva_rect, "Human vs AI", PLAYER2_COLOR)
        
        instruction_lines = [
            "• Click cell to select move",
            "• LEFT/RIGHT arrows for direction", 
            "• Player 2 directions are reversed",
            "• Can capture quan (big cells) when empty-occupied pattern",
            "• Auto redistribute when out of stones (costs 5 points)",
            "• Game ends when both quan are captured",
            "• R: Restart, M: Menu"
        ]
        
        for i, line in enumerate(instruction_lines):
            text_surface = self.small_font.render(line, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 480 + i * 25))
            self.screen.blit(text_surface, text_rect)
        
        return hvh_rect, hva_rect

    def draw_button(self, rect, text, color):
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect)
        
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def draw_board(self):
        self.draw_gradient_background()
        
        title_surface = self.font.render("O AN QUAN", True, TEXT_COLOR)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH//2, 40))
        self.screen.blit(title_surface, title_rect)
        
        board_bg = pygame.Rect(40, 200, WINDOW_WIDTH - 80, 350)
        pygame.draw.rect(self.screen, (160, 130, 90), board_bg)
        pygame.draw.rect(self.screen, TEXT_COLOR, board_bg, 4)
        
        cell_width, cell_height = 120, 90
        start_x, start_y = 180, 250
        cell_rects = {}
        
        self.draw_quan_cell(6, 70, start_y + 50)
        self.draw_quan_cell(12, WINDOW_WIDTH - 190, start_y + 50)
        
        valid_moves = self.game_state.get_valid_moves()
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            cell_index = 5 - i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            
            color = self.get_cell_color(cell_index, valid_moves)
            self.draw_cell(rect, color, cell_index)
            cell_rects[cell_index] = rect
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            cell_index = 7 + i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            
            color = self.get_cell_color(cell_index, valid_moves)
            self.draw_cell(rect, color, cell_index)
            cell_rects[cell_index] = rect
        
        self.draw_game_info()
        
        if self.animation.sowing_visible:
            x, y = self.animation.sowing_position
            self.draw_sowing_hand(self.screen, int(x), int(y))
        
        self.draw_flying_stones(self.screen)
        if self.animation.hand_visible:
            x, y = self.animation.hand_position
            self.draw_hand_effect(self.screen, int(x), int(y), self.animation.captured_stones)
        
        if self.waiting_for_direction:
            if self.game_state.current_player == Player.PLAYER1:
                instruction = "Press LEFT (counter-clockwise) or RIGHT (clockwise) arrow"
            else:
                instruction = "Press LEFT (clockwise) or RIGHT (counter-clockwise) arrow"
            
            text_surface = self.small_font.render(instruction, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 580))
            
            bg_rect = text_rect.copy()
            bg_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, bg_rect, 2)
            
            self.screen.blit(text_surface, text_rect)
        
        if not valid_moves and not self.game_state.game_over:
            player_name = "Player 1" if self.game_state.current_player == Player.PLAYER1 else "Player 2"
            score = self.game_state.player1_score if self.game_state.current_player == Player.PLAYER1 else self.game_state.player2_score
            
            if score >= 5:
                msg = f"{player_name} out of stones! Auto redistributing..."
                text_surface = self.small_font.render(msg, True, (255, 0, 0))
                text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 600))
                
                bg_rect = text_rect.copy()
                bg_rect.inflate(20, 10)
                pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
                pygame.draw.rect(self.screen, (255, 0, 0), bg_rect, 2)
                
                self.screen.blit(text_surface, text_rect)
        
        return cell_rects

    def get_cell_color(self, cell_index, valid_moves):
        if self.selected_cell == cell_index:
            return HIGHLIGHT_COLOR
        elif cell_index in valid_moves:
            if ((self.game_state.current_player == Player.PLAYER1 and 7 <= cell_index <= 11) or 
                (self.game_state.current_player == Player.PLAYER2 and 1 <= cell_index <= 5)):
                return VALID_MOVE_COLOR
        
        return BOARD_COLOR

    def draw_quan_cell(self, index, x, y):
        rect = pygame.Rect(x, y, 120, 120)
        color = HIGHLIGHT_COLOR if self.selected_cell == index else QUAN_COLOR
        
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect)
        
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 4)
        
        stones = self.game_state.board[index]
        if stones > 0:
            self.draw_stones_in_quan(rect, stones, index)

    def draw_stones_in_quan(self, rect, stones, cell_index):
        is_being_captured = (self.animation.capturing and 
                           cell_index in self.animation.capture_positions)
        
        if stones <= 12:
            for i in range(stones):
                angle = i * 2 * math.pi / stones if stones > 1 else 0
                stone_x = rect.centerx + 30 * math.cos(angle)
                stone_y = rect.centery + 30 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_quan=True, is_capturing=is_being_captured)
        elif stones <= 24:
            outer_count = min(12, stones)
            inner_count = stones - outer_count
            
            for i in range(outer_count):
                angle = i * 2 * math.pi / outer_count
                stone_x = rect.centerx + 35 * math.cos(angle)
                stone_y = rect.centery + 35 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_quan=True, is_capturing=is_being_captured)
            
            for i in range(inner_count):
                angle = i * 2 * math.pi / inner_count if inner_count > 1 else 0
                stone_x = rect.centerx + 15 * math.cos(angle)
                stone_y = rect.centery + 15 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_quan=True, is_capturing=is_being_captured, size_factor=0.7)
        else:
            for i in range(8):
                angle = i * 2 * math.pi / 8
                stone_x = rect.centerx + 30 * math.cos(angle)
                stone_y = rect.centery + 30 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_quan=True, is_capturing=is_being_captured)
            
            count_text = self.font.render(str(stones), True, TEXT_COLOR)
            count_rect = count_text.get_rect(center=(rect.centerx, rect.y - 20))
            
            bg_rect = count_rect.copy()
            bg_rect.inflate(10, 5)
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, bg_rect, 2)
            
            self.screen.blit(count_text, count_rect)

    def draw_cell(self, rect, color, cell_index):
        shadow_rect = rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(self.screen, (80, 80, 80), shadow_rect)
        
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        stones = self.game_state.board[cell_index]
        if stones > 0:
            self.draw_stones_in_cell(rect, stones, cell_index)

    def draw_stones_in_cell(self, rect, stones, cell_index):
        is_being_captured = (self.animation.capturing and 
                           cell_index in self.animation.capture_positions)
        
        is_moving = (self.animation.is_animating and 
                   self.animation.current_position == cell_index and 
                   self.animation.current_stones > 0)
        
        if stones <= 8:
            for i in range(stones):
                angle = i * 2 * math.pi / stones if stones > 1 else 0
                stone_x = rect.centerx + 20 * math.cos(angle)
                stone_y = rect.centery + 20 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_moving=is_moving, is_capturing=is_being_captured)
        elif stones <= 16:
            outer_count = min(8, stones)
            inner_count = stones - outer_count
            
            for i in range(outer_count):
                angle = i * 2 * math.pi / outer_count
                stone_x = rect.centerx + 25 * math.cos(angle)
                stone_y = rect.centery + 25 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_moving=is_moving, is_capturing=is_being_captured)
            
            for i in range(inner_count):
                angle = i * 2 * math.pi / inner_count if inner_count > 1 else 0
                stone_x = rect.centerx + 10 * math.cos(angle)
                stone_y = rect.centery + 10 * math.sin(angle)
                self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                 is_moving=is_moving, is_capturing=is_being_captured, size_factor=0.7)
        elif stones <= 24:
            circles = [
                {'radius': 28, 'count': 8, 'size': 1.0},
                {'radius': 15, 'count': 8, 'size': 0.8},
                {'radius': 5, 'count': stones - 16, 'size': 0.6}
            ]
            
            stone_drawn = 0
            for circle in circles:
                count = min(circle['count'], stones - stone_drawn)
                if count <= 0:
                    break
                    
                for i in range(count):
                    angle = i * 2 * math.pi / count if count > 1 else 0
                    stone_x = rect.centerx + circle['radius'] * math.cos(angle)
                    stone_y = rect.centery + circle['radius'] * math.sin(angle)
                    self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                     is_moving=is_moving, is_capturing=is_being_captured, 
                                     size_factor=circle['size'])
                stone_drawn += count
        else:
            max_display = 20
            cols = 5
            rows = 4
            
            start_x = rect.x + 15
            start_y = rect.y + 15
            spacing = 18
            
            for i in range(min(stones, max_display)):
                row = i // cols
                col = i % cols
                stone_x = start_x + col * spacing
                stone_y = start_y + row * spacing
                self.draw_stone_3d(self.screen, stone_x, stone_y, 
                                 is_moving=is_moving, is_capturing=is_being_captured, 
                                 size_factor=0.6)
            
            if stones > max_display:
                count_text = self.small_font.render(f"{stones}", True, TEXT_COLOR)
                count_rect = count_text.get_rect(center=(rect.centerx, rect.bottom - 8))
                
                bg_rect = count_rect.copy()
                bg_rect.inflate(8, 4)
                pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
                pygame.draw.rect(self.screen, TEXT_COLOR, bg_rect, 1)
                
                self.screen.blit(count_text, count_rect)

    def draw_game_info(self):
        p1_rect = pygame.Rect(50, 80, 180, 80)
        p2_rect = pygame.Rect(WINDOW_WIDTH - 230, 80, 180, 80)
        
        self.draw_score_panel(p1_rect, "Player 1", self.game_state.player1_score, PLAYER1_COLOR)
        
        p2_name = "Player 2" if self.game_mode == GameMode.HUMAN_VS_HUMAN else "Computer"
        self.draw_score_panel(p2_rect, p2_name, self.game_state.player2_score, PLAYER2_COLOR)
        
        if not self.game_state.game_over and not self.animation.is_animating:
            current_name = "Player 1" if self.game_state.current_player == Player.PLAYER1 else p2_name
            color = PLAYER1_COLOR if self.game_state.current_player == Player.PLAYER1 else PLAYER2_COLOR
            
            turn_rect = pygame.Rect(WINDOW_WIDTH//2 - 120, 100, 240, 35)
            pygame.draw.rect(self.screen, color, turn_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, turn_rect, 2)
            
            turn_text = self.small_font.render(f"Turn: {current_name}", True, (255, 255, 255))
            turn_text_rect = turn_text.get_rect(center=turn_rect.center)
            self.screen.blit(turn_text, turn_text_rect)

    def draw_score_panel(self, rect, name, score, color):
        glow = (self.animation.score_effect and 
                ((self.animation.score_effect_player == Player.PLAYER1 and "Player 1" in name) or
                 (self.animation.score_effect_player == Player.PLAYER2 and ("Player 2" in name or "Computer" in name))))
        
        if glow:
            glow_rect = rect.copy()
            glow_rect.inflate(10, 10)
            glow_color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50))
            pygame.draw.rect(self.screen, glow_color, glow_rect)
        
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        name_surface = self.small_font.render(name, True, (255, 255, 255))
        score_surface = self.font.render(str(score), True, (255, 255, 255))
        
        if glow:
            pulse = 1.0 + 0.3 * math.sin(self.animation.score_effect_frame * 0.5)
            font_size = int(28 * pulse)
            pulse_font = pygame.font.Font(None, font_size)
            score_surface = pulse_font.render(str(score), True, (255, 255, 100))
        
        name_rect = name_surface.get_rect(center=(rect.centerx, rect.y + 20))
        score_rect = score_surface.get_rect(center=(rect.centerx, rect.y + 50))
        
        self.screen.blit(name_surface, name_rect)
        self.screen.blit(score_surface, score_rect)

    def handle_click(self, pos, cell_rects):
        if self.animation.is_animating or self.animation.capturing:
            return
        
        if self.check_auto_redistribute():
            return
        
        for cell_index, rect in cell_rects.items():
            if rect.collidepoint(pos):
                if cell_index in self.game_state.get_valid_moves():
                    if self.game_mode == GameMode.HUMAN_VS_AI and self.game_state.current_player == Player.PLAYER2:
                        return
                    
                    self.selected_cell = cell_index
                    self.waiting_for_direction = True

    def handle_direction_key(self, direction):
        if not self.waiting_for_direction or self.selected_cell is None:
            return
        
        self.waiting_for_direction = False
        
        stones = self.game_state.board[self.selected_cell]
        if stones > 0:
            self.start_animation(self.selected_cell, direction, self.finish_move)
        else:
            self.game_state._redistribute_stones()
            self.game_state.current_player = Player.PLAYER2 if self.game_state.current_player == Player.PLAYER1 else Player.PLAYER1
        
        self.selected_cell = None

    def finish_move(self, last_position):
        # Get positions to capture
        capture_positions = self.game_state._capture_stones_correct(last_position, self.animation.direction)
        
        # Start capture animation if there are positions to capture
        if capture_positions:
            self.start_capture_animation(capture_positions, self.finish_turn)
        else:
            self.finish_turn(None)

    def finish_turn(self, _):
        self.game_state._check_game_over()
        
        if not self.game_state.game_over:
            self.game_state.current_player = Player.PLAYER2 if self.game_state.current_player == Player.PLAYER1 else Player.PLAYER1
            
            if self.check_auto_redistribute():
                pass
            
            if (self.game_mode == GameMode.HUMAN_VS_AI and 
                self.game_state.current_player == Player.PLAYER2 and 
                not self.game_state.game_over):
                pygame.time.set_timer(pygame.USEREVENT + 1, 2000)

        self.game_state.move_count += 1

    def ai_move(self):
        if (self.game_state.current_player == Player.PLAYER2 and 
            not self.game_state.game_over and 
            not self.animation.is_animating and
            not self.animation.capturing):
            
            if self.check_auto_redistribute():
                return
                
            best_move, best_direction = self.ai_engine.get_best_move(self.game_state)
            if best_move is not None:
                stones = self.game_state.board[best_move]
                if stones > 0:
                    self.start_animation(best_move, best_direction, self.finish_move)
                else:
                    self.game_state._redistribute_stones()
                    self.game_state.current_player = Player.PLAYER1

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        result_rect = pygame.Rect(WINDOW_WIDTH//2 - 250, WINDOW_HEIGHT//2 - 120, 500, 240)
        pygame.draw.rect(self.screen, (240, 240, 240), result_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, result_rect, 4)
        
        if self.game_state.winner == Player.PLAYER1:
            winner_text = "Player 1 Wins!"
            color = PLAYER1_COLOR
        elif self.game_state.winner == Player.PLAYER2:
            winner_text = "Player 2 Wins!" if self.game_mode == GameMode.HUMAN_VS_HUMAN else "Computer Wins!"
            color = PLAYER2_COLOR
        else:
            winner_text = "Draw!"
            color = TEXT_COLOR
        
        winner_surface = self.font.render(winner_text, True, color)
        winner_rect = winner_surface.get_rect(center=(result_rect.centerx, result_rect.centery - 40))
        self.screen.blit(winner_surface, winner_rect)
        
        score_text = f"Score: {self.game_state.player1_score} - {self.game_state.player2_score}"
        score_surface = self.font.render(score_text, True, TEXT_COLOR)
        score_rect = score_surface.get_rect(center=(result_rect.centerx, result_rect.centery))
        self.screen.blit(score_surface, score_rect)
        
        restart_text = "Press R to restart"
        menu_text = "Press M for main menu"
        
        restart_surface = self.small_font.render(restart_text, True, TEXT_COLOR)
        menu_surface = self.small_font.render(menu_text, True, TEXT_COLOR)
        
        restart_rect = restart_surface.get_rect(center=(result_rect.centerx, result_rect.centery + 40))
        menu_rect = menu_surface.get_rect(center=(result_rect.centerx, result_rect.centery + 65))
        
        self.screen.blit(restart_surface, restart_rect)
        self.screen.blit(menu_surface, menu_rect)

    def get_cell_rects(self):
        cell_width, cell_height = 120, 90
        start_x, start_y = 180, 250
        cell_rects = {}
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            cell_index = 5 - i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            cell_rects[cell_index] = rect
        
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            cell_index = 7 + i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            cell_rects[cell_index] = rect
        
        return cell_rects

    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.in_menu:
                        hvh_rect, hva_rect = self.draw_menu()
                        if hvh_rect.collidepoint(event.pos):
                            self.game_mode = GameMode.HUMAN_VS_HUMAN
                            self.in_menu = False
                        elif hva_rect.collidepoint(event.pos):
                            self.game_mode = GameMode.HUMAN_VS_AI
                            self.in_menu = False
                    else:
                        if not self.game_state.game_over:
                            temp_rects = self.get_cell_rects()
                            self.handle_click(event.pos, temp_rects)
                
                elif event.type == pygame.USEREVENT + 1:
                    self.ai_move()
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.game_state = GameState()
                        self.animation = AnimationState()
                        self.selected_cell = None
                        self.waiting_for_direction = False
                    elif event.key == pygame.K_m:
                        self.in_menu = True
                        self.game_state = GameState()
                        self.animation = AnimationState()
                        self.selected_cell = None
                        self.waiting_for_direction = False
                    elif event.key == pygame.K_LEFT:
                        if self.game_state.current_player == Player.PLAYER1:
                            self.handle_direction_key(Direction.COUNTER_CLOCKWISE)
                        else:
                            self.handle_direction_key(Direction.CLOCKWISE)
                    elif event.key == pygame.K_RIGHT:
                        if self.game_state.current_player == Player.PLAYER1:
                            self.handle_direction_key(Direction.CLOCKWISE)
                        else:
                            self.handle_direction_key(Direction.COUNTER_CLOCKWISE)
            
            if not self.animation.is_animating and not self.animation.capturing and not self.game_state.game_over:
                self.check_auto_redistribute()
            
            self.update_animation()
            
            if self.in_menu:
                self.draw_menu()
            else:
                self.draw_board()
                if self.game_state.game_over:
                    self.draw_game_over()
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = OAnQuanGame()
    game.run()
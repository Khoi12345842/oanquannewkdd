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
        self.animation_speed = 25  # slower: 25 frames per stone
        self.frame_count = 0
        self.callback = None
        self.direction = Direction.CLOCKWISE
        
        # Capture animation
        self.capturing = False
        self.capture_positions = []
        self.capture_frame = 0
        self.capture_speed = 8  # frames per capture step
        
        # Hand animation
        self.hand_visible = False
        self.hand_position = None
        self.hand_target = None
        self.hand_frame = 0
        self.captured_stones = 0
        
        # Score effect
        self.score_effect = False
        self.score_effect_frame = 0
        self.score_effect_player = None

class GameState:
    def __init__(self):
        # Board: [0, P2_5, P2_4, P2_3, P2_2, P2_1, L_quan, P1_1, P1_2, P1_3, P1_4, P1_5, R_quan]
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
        
        # If no moves, allow redistribution
        if not moves:
            if (self.current_player == Player.PLAYER1 and self.player1_score >= 5) or \
               (self.current_player == Player.PLAYER2 and self.player2_score >= 5):
                if self.current_player == Player.PLAYER1:
                    moves = list(range(7, 12))
                else:
                    moves = list(range(1, 6))
        
        return moves

    def make_move_instant(self, position: int, direction: Direction) -> bool:
        """For AI - no animation"""
        if position not in self.get_valid_moves():
            return False
        
        if self.board[position] == 0:
            self._redistribute_stones()
            return True
        
        # Move stones according to correct logic
        current_pos = position
        stones = self.board[position]
        self.board[position] = 0
        
        # Continue moving stones until we can't
        while stones > 0:
            # Distribute stones
            while stones > 0:
                current_pos = self._next_position(current_pos, direction)
                self.board[current_pos] += 1
                stones -= 1
            
            # Check next position after last stone
            next_pos = self._next_position(current_pos, direction)
            
            # If next position is quan, stop turn
            if next_pos == 6 or next_pos == 12:
                break
            
            # If next position has stones, continue moving
            if self.board[next_pos] > 0:
                stones = self.board[next_pos]
                self.board[next_pos] = 0
                current_pos = next_pos
            else:
                # Next position is empty, try to capture
                self._capture_stones_correct(current_pos, direction)
                break
        
        self._check_game_over()
        
        if not self.game_over:
            self.current_player = Player.PLAYER2 if self.current_player == Player.PLAYER1 else Player.PLAYER1
        
        self.move_count += 1
        return True

    def _next_position(self, pos: int, direction: Direction) -> int:
        """Calculate next position based on direction"""
        if direction == Direction.CLOCKWISE:
            next_pos = (pos + 1) % 13
            if next_pos == 0:
                next_pos = 1
        else:  # COUNTER_CLOCKWISE
            next_pos = (pos - 1) % 13
            if next_pos == 0:
                next_pos = 12
        return next_pos

    def _capture_stones_correct(self, last_position: int, direction: Direction):
        """Correct capture logic"""
        current_pos = last_position
        
        while True:
            next_pos = self._next_position(current_pos, direction)
            
            # If next position is empty
            if self.board[next_pos] == 0:
                # Look for position after empty to capture
                capture_pos = self._next_position(next_pos, direction)
                
                # If position after empty has stones
                if self.board[capture_pos] > 0:
                    # Capture stones
                    captured = self.board[capture_pos]
                    self.board[capture_pos] = 0
                    
                    if self.current_player == Player.PLAYER1:
                        self.player1_score += captured
                    else:
                        self.player2_score += captured
                    
                    # Continue checking
                    current_pos = capture_pos
                else:
                    # No stones to capture, stop
                    break
            else:
                # Next position has stones, stop capturing
                break

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
        if self.board[6] == 0 and self.board[12] == 0:
            self.game_over = True
            # Collect remaining stones
            for i in range(1, 6):
                self.player2_score += self.board[i]
                self.board[i] = 0
            for i in range(7, 12):
                self.player1_score += self.board[i]
                self.board[i] = 0
            
            if self.player1_score > self.player2_score:
                self.winner = Player.PLAYER1
            elif self.player2_score > self.player1_score:
                self.winner = Player.PLAYER2
            else:
                self.winner = None

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
        
        # Initialize fonts
        self.init_fonts()
        
        self.game_state = GameState()
        self.ai_engine = AIEngine(max_depth=4)
        self.game_mode = GameMode.HUMAN_VS_HUMAN
        self.selected_cell = None
        self.waiting_for_direction = False
        self.animation = AnimationState()
        
        self.in_menu = True
        self.cell_positions = {}
        self.setup_cell_positions()

    def init_fonts(self):
        """Initialize fonts"""
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
        
        # Left quan (index 6)
        self.cell_positions[6] = (70, start_y + cell_height//2 + 50)
        
        # Right quan (index 12)
        self.cell_positions[12] = (WINDOW_WIDTH - 130, start_y + cell_height//2 + 50)
        
        # Top row (Player 2) - indices 5,4,3,2,1
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            self.cell_positions[5-i] = (x + cell_width//2, y + cell_height//2)
        
        # Bottom row (Player 1) - indices 7,8,9,10,11
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            self.cell_positions[7+i] = (x + cell_width//2, y + cell_height//2)

    def start_animation(self, start_pos: int, direction: Direction, callback=None):
        self.animation.is_animating = True
        self.animation.current_stones = self.game_state.board[start_pos]
        self.animation.current_position = start_pos
        self.animation.frame_count = 0
        self.animation.callback = callback
        self.animation.direction = direction
        
        # Clear starting position
        self.game_state.board[start_pos] = 0

    def update_animation(self):
        if self.animation.capturing:
            self.update_capture_animation()
            
        self.update_hand_animation()
        self.update_score_effect()
            
        if not self.animation.is_animating:
            return
        
        self.animation.frame_count += 1
        
        if self.animation.frame_count >= self.animation.animation_speed:
            self.animation.frame_count = 0
            
            if self.animation.current_stones > 0:
                # Move to next position
                self.animation.current_position = self.game_state._next_position(
                    self.animation.current_position, self.animation.direction
                )
                
                # Place stone
                self.game_state.board[self.animation.current_position] += 1
                self.animation.current_stones -= 1
            else:
                # Animation finished, check for continuation
                next_pos = self.game_state._next_position(
                    self.animation.current_position, self.animation.direction
                )
                
                # If next is quan, stop
                if next_pos == 6 or next_pos == 12:
                    self.animation.is_animating = False
                    if self.animation.callback:
                        self.animation.callback(self.animation.current_position)
                # If next has stones, continue
                elif self.game_state.board[next_pos] > 0:
                    self.animation.current_stones = self.game_state.board[next_pos]
                    self.game_state.board[next_pos] = 0
                    self.animation.current_position = next_pos
                else:
                    # Next is empty, finish
                    self.animation.is_animating = False
                    if self.animation.callback:
                        self.animation.callback(self.animation.current_position)

    def update_capture_animation(self):
        """Update capture animation with enhanced hand effect"""
        self.animation.capture_frame += 1
        
        if self.animation.capture_frame >= self.animation.capture_speed:
            self.animation.capture_frame = 0
            
            if self.animation.capture_positions:
                # Capture one position at a time
                pos = self.animation.capture_positions.pop(0)
                captured = self.game_state.board[pos]
                self.game_state.board[pos] = 0
                
                # Start hand animation
                self.start_hand_animation(pos, captured)
                
                # Add to score
                if self.game_state.current_player == Player.PLAYER1:
                    self.game_state.player1_score += captured
                else:
                    self.game_state.player2_score += captured
                
                # Start score effect
                self.animation.score_effect = True
                self.animation.score_effect_frame = 0
                self.animation.score_effect_player = self.game_state.current_player
                
            else:
                # Capturing finished
                self.animation.capturing = False
                if self.animation.callback:
                    self.animation.callback(None)

    def start_hand_animation(self, from_pos, stones):
        """Start hand animation from position to score area"""
        if from_pos in self.cell_positions:
            self.animation.hand_visible = True
            self.animation.hand_position = list(self.cell_positions[from_pos])
            self.animation.captured_stones = stones
            self.animation.hand_frame = 0
            
            # Target position (score area)
            if self.game_state.current_player == Player.PLAYER1:
                self.animation.hand_target = [130, 120]  # Player 1 score area
            else:
                self.animation.hand_target = [WINDOW_WIDTH - 150, 120]  # Player 2 score area

    def update_hand_animation(self):
        """Update hand movement animation"""
        if not self.animation.hand_visible:
            return
            
        self.animation.hand_frame += 1
        
        if self.animation.hand_frame < 30:  # 30 frames to move
            # Interpolate position
            progress = self.animation.hand_frame / 30
            start_x, start_y = self.animation.hand_position
            target_x, target_y = self.animation.hand_target
            
            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress
            
            self.animation.hand_position = [current_x, current_y]
        else:
            # Animation finished
            self.animation.hand_visible = False
            
    def update_score_effect(self):
        """Update score increase effect"""
        if self.animation.score_effect:
            self.animation.score_effect_frame += 1
            if self.animation.score_effect_frame > 20:  # Effect lasts 20 frames
                self.animation.score_effect = False

    def start_capture_animation(self, positions, callback=None):
        """Start animated capture sequence"""
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

    def draw_stone_3d(self, surface, x, y, is_quan=False, is_moving=False, is_capturing=False):
        if is_quan:
            radius = 18
            color = QUAN_COLOR
        else:
            radius = 12
            color = STONE_COLOR
        
        if is_moving:
            color = ANIMATION_COLOR
            radius += 3
        elif is_capturing:
            color = (255, 100, 100)  # Red for capturing
            radius += 2
        
        # Shadow
        pygame.draw.circle(surface, (0, 0, 0), (x + 3, y + 3), radius)
        
        # Main stone
        pygame.draw.circle(surface, color, (x, y), radius)
        
        # Highlight
        highlight_color = (min(255, color[0] + 60), min(255, color[1] + 60), min(255, color[2] + 60))
        pygame.draw.circle(surface, highlight_color, (x - radius//3, y - radius//3), radius//3)

    def draw_hand_effect(self, surface, x, y, stones=0):
        """Draw enhanced hand grabbing effect"""
        if not self.animation.hand_visible:
            return
            
        # Hand base
        hand_points = [
            (x - 12, y - 18), (x - 6, y - 22), (x, y - 20),
            (x + 6, y - 22), (x + 12, y - 18), (x + 10, y - 8),
            (x + 6, y - 2), (x - 6, y - 2), (x - 10, y - 8)
        ]
        
        # Hand shadow
        shadow_points = [(px + 2, py + 2) for px, py in hand_points]
        pygame.draw.polygon(surface, (100, 100, 100), shadow_points)
        
        # Main hand
        pygame.draw.polygon(surface, (255, 220, 177), hand_points)  # Skin color
        pygame.draw.polygon(surface, (200, 180, 140), hand_points, 2)  # Outline
        
        # Fingers detail
        finger_positions = [(x-8, y-15), (x-3, y-18), (x+3, y-18), (x+8, y-15)]
        for fx, fy in finger_positions:
            pygame.draw.circle(surface, (240, 200, 160), (fx, fy), 3)
            pygame.draw.circle(surface, (200, 180, 140), (fx, fy), 3, 1)
        
        # Show stones being held
        if stones > 0:
            for i in range(min(stones, 3)):  # Show max 3 stones
                stone_x = x + (i - 1) * 6
                stone_y = y - 5
                pygame.draw.circle(surface, STONE_COLOR, (stone_x, stone_y), 4)
                pygame.draw.circle(surface, (150, 150, 150), (stone_x, stone_y), 4, 1)
            
            if stones > 3:
                # Show count
                count_text = pygame.font.Font(None, 16).render(f"+{stones-3}", True, TEXT_COLOR)
                surface.blit(count_text, (x - 8, y + 5))

    def draw_flying_stones(self, surface):
        """Draw stones flying to score area"""
        if self.animation.hand_visible and self.animation.captured_stones > 0:
            x, y = self.animation.hand_position
            
            # Draw small stones around the hand
            for i in range(min(self.animation.captured_stones, 5)):
                angle = i * 2 * math.pi / 5
                stone_x = x + 15 * math.cos(angle)
                stone_y = y + 15 * math.sin(angle)
                
                # Make stones semi-transparent and glowing
                stone_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(stone_surface, (*STONE_COLOR, 180), (5, 5), 4)
                pygame.draw.circle(stone_surface, (255, 255, 255, 100), (3, 3), 2)
                surface.blit(stone_surface, (stone_x - 5, stone_y - 5))

    def draw_direction_arrows(self, cell_rect, cell_index):
        """Draw direction choice arrows"""
        if not self.showing_direction_choice or self.selected_cell != cell_index:
            return None, None
        
        # Arrow positions
        left_arrow_rect = pygame.Rect(cell_rect.x - 40, cell_rect.centery - 15, 30, 30)
        right_arrow_rect = pygame.Rect(cell_rect.right + 10, cell_rect.centery - 15, 30, 30)
        
        # Draw arrow backgrounds
        pygame.draw.rect(self.screen, DIRECTION_COLOR, left_arrow_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, left_arrow_rect, 2)
        pygame.draw.rect(self.screen, DIRECTION_COLOR, right_arrow_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, right_arrow_rect, 2)
        
        # Draw arrows
        # Left arrow (counter-clockwise)
        left_points = [
            (left_arrow_rect.right - 8, left_arrow_rect.y + 5),
            (left_arrow_rect.x + 8, left_arrow_rect.centery),
            (left_arrow_rect.right - 8, left_arrow_rect.bottom - 5)
        ]
        pygame.draw.polygon(self.screen, ARROW_COLOR, left_points)
        
        # Right arrow (clockwise)
        right_points = [
            (right_arrow_rect.x + 8, right_arrow_rect.y + 5),
            (right_arrow_rect.right - 8, right_arrow_rect.centery),
            (right_arrow_rect.x + 8, right_arrow_rect.bottom - 5)
        ]
        pygame.draw.polygon(self.screen, ARROW_COLOR, right_points)
        
        return left_arrow_rect, right_arrow_rect

    def draw_menu(self):
        self.draw_gradient_background()
        
        # Title
        title_text = "O AN QUAN"
        title_surface = self.title_font.render(title_text, True, TEXT_COLOR)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH//2, 120))
        self.screen.blit(title_surface, title_rect)
        
        # Subtitle
        subtitle_text = "Vietnamese Traditional Game"
        subtitle_surface = self.small_font.render(subtitle_text, True, TEXT_COLOR)
        subtitle_rect = subtitle_surface.get_rect(center=(WINDOW_WIDTH//2, 170))
        self.screen.blit(subtitle_surface, subtitle_rect)
        
        # Buttons
        button_width, button_height = 300, 70
        hvh_rect = pygame.Rect(WINDOW_WIDTH//2 - button_width//2, 250, button_width, button_height)
        hva_rect = pygame.Rect(WINDOW_WIDTH//2 - button_width//2, 350, button_width, button_height)
        
        self.draw_button(hvh_rect, "Human vs Human", PLAYER1_COLOR)
        self.draw_button(hva_rect, "Human vs AI", PLAYER2_COLOR)
        
        # Instructions
        instruction_lines = [
            "• Click cell to select move",
            "• LEFT/RIGHT arrows for direction",
            "• Player 2 directions are reversed",
            "• R: Restart, M: Menu"
        ]
        
        for i, line in enumerate(instruction_lines):
            text_surface = self.small_font.render(line, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 480 + i * 25))
            self.screen.blit(text_surface, text_rect)
        
        return hvh_rect, hva_rect

    def draw_button(self, rect, text, color):
        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect)
        
        # Button
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        # Text
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def draw_board(self):
        self.draw_gradient_background()
        
        # Title
        title_surface = self.font.render("O AN QUAN", True, TEXT_COLOR)
        title_rect = title_surface.get_rect(center=(WINDOW_WIDTH//2, 40))
        self.screen.blit(title_surface, title_rect)
        
        # Board background
        board_bg = pygame.Rect(40, 200, WINDOW_WIDTH - 80, 350)
        pygame.draw.rect(self.screen, (160, 130, 90), board_bg)
        pygame.draw.rect(self.screen, TEXT_COLOR, board_bg, 4)
        
        cell_width, cell_height = 120, 90
        start_x, start_y = 180, 250
        cell_rects = {}
        
        # Draw quan cells
        self.draw_quan_cell(6, 70, start_y + 50)
        self.draw_quan_cell(12, WINDOW_WIDTH - 190, start_y + 50)
        
        # Draw player cells
        valid_moves = self.game_state.get_valid_moves()
        
        # Top row (Player 2)
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            cell_index = 5 - i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            
            color = self.get_cell_color(cell_index, valid_moves)
            self.draw_cell(rect, color, cell_index)
            cell_rects[cell_index] = rect
        
        # Bottom row (Player 1)
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            cell_index = 7 + i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            
            color = self.get_cell_color(cell_index, valid_moves)
            self.draw_cell(rect, color, cell_index)
            cell_rects[cell_index] = rect
        
        # Draw game info
        self.draw_game_info()
        
        # Draw flying stones and hand effects
        self.draw_flying_stones(self.screen)
        if self.animation.hand_visible:
            x, y = self.animation.hand_position
            self.draw_hand_effect(self.screen, int(x), int(y), self.animation.captured_stones)
        
        # Show direction instruction if waiting for direction
        if self.waiting_for_direction:
            if self.game_state.current_player == Player.PLAYER1:
                instruction = "Press LEFT (counter-clockwise) or RIGHT (clockwise) arrow"
            else:
                instruction = "Press LEFT (clockwise) or RIGHT (counter-clockwise) arrow"
            
            text_surface = self.small_font.render(instruction, True, TEXT_COLOR)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, 580))
            
            # Background for instruction
            bg_rect = text_rect.copy()
            bg_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)
            pygame.draw.rect(self.screen, TEXT_COLOR, bg_rect, 2)
            
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
        
        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (50, 50, 50), shadow_rect)
        
        # Main rect
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 4)
        
        # Draw stones
        stones = self.game_state.board[index]
        if stones > 0:
            if stones <= 8:
                for i in range(stones):
                    angle = i * 2 * math.pi / stones
                    stone_x = rect.centerx + 35 * math.cos(angle)
                    stone_y = rect.centery + 35 * math.sin(angle)
                    self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), is_quan=True)
            else:
                for i in range(6):
                    angle = i * 2 * math.pi / 6
                    stone_x = rect.centerx + 35 * math.cos(angle)
                    stone_y = rect.centery + 35 * math.sin(angle)
                    self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), is_quan=True)
                
                count_text = self.small_font.render(f"+{stones-6}", True, TEXT_COLOR)
                count_rect = count_text.get_rect(center=(rect.centerx, rect.y - 15))
                self.screen.blit(count_text, count_rect)

    def draw_cell(self, rect, color, cell_index):
        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(self.screen, (80, 80, 80), shadow_rect)
        
        # Main rect
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        # Check if this cell is being captured
        is_being_captured = (self.animation.capturing and 
                           cell_index in self.animation.capture_positions)
        
        # Draw stones
        stones = self.game_state.board[cell_index]
        if stones > 0:
            if stones <= 8:
                for i in range(stones):
                    angle = i * 2 * math.pi / stones if stones > 1 else 0
                    stone_x = rect.centerx + 25 * math.cos(angle)
                    stone_y = rect.centery + 25 * math.sin(angle)
                    
                    is_moving = (self.animation.is_animating and 
                               self.animation.current_position == cell_index and 
                               self.animation.current_stones > 0)
                    
                    self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                     is_moving=is_moving, is_capturing=is_being_captured)
            else:
                for i in range(6):
                    angle = i * 2 * math.pi / 6
                    stone_x = rect.centerx + 25 * math.cos(angle)
                    stone_y = rect.centery + 25 * math.sin(angle)
                    self.draw_stone_3d(self.screen, int(stone_x), int(stone_y), 
                                     is_capturing=is_being_captured)
                
                count_text = self.small_font.render(f"+{stones-6}", True, TEXT_COLOR)
                count_rect = count_text.get_rect(center=(rect.centerx, rect.y - 12))
                self.screen.blit(count_text, count_rect)

    def draw_game_info(self):
        # Score panels
        p1_rect = pygame.Rect(50, 80, 180, 80)
        p2_rect = pygame.Rect(WINDOW_WIDTH - 230, 80, 180, 80)
        
        self.draw_score_panel(p1_rect, "Player 1", self.game_state.player1_score, PLAYER1_COLOR)
        
        p2_name = "Player 2" if self.game_mode == GameMode.HUMAN_VS_HUMAN else "Computer"
        self.draw_score_panel(p2_rect, p2_name, self.game_state.player2_score, PLAYER2_COLOR)
        
        # Turn indicator
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
        # Enhanced background with glow effect if score increased
        glow = (self.animation.score_effect and 
                ((self.animation.score_effect_player == Player.PLAYER1 and "Player 1" in name) or
                 (self.animation.score_effect_player == Player.PLAYER2 and ("Player 2" in name or "Computer" in name))))
        
        if glow:
            # Glow effect
            glow_rect = rect.copy()
            glow_rect.inflate(10, 10)
            glow_color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50))
            pygame.draw.rect(self.screen, glow_color, glow_rect)
        
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, rect, 3)
        
        name_surface = self.small_font.render(name, True, (255, 255, 255))
        score_surface = self.font.render(str(score), True, (255, 255, 255))
        
        # Add pulsing effect to score if it just increased
        if glow:
            pulse = 1.0 + 0.3 * math.sin(self.animation.score_effect_frame * 0.5)
            font_size = int(28 * pulse)
            pulse_font = pygame.font.Font(None, font_size)
            score_surface = pulse_font.render(str(score), True, (255, 255, 100))  # Yellow highlight
        
        name_rect = name_surface.get_rect(center=(rect.centerx, rect.y + 20))
        score_rect = score_surface.get_rect(center=(rect.centerx, rect.y + 50))
        
        self.screen.blit(name_surface, name_rect)
        self.screen.blit(score_surface, score_rect)

    def handle_click(self, pos, cell_rects):
        if self.animation.is_animating or self.animation.capturing:
            return
        
        # Check cell clicks
        for cell_index, rect in cell_rects.items():
            if rect.collidepoint(pos):
                if cell_index in self.game_state.get_valid_moves():
                    if self.game_mode == GameMode.HUMAN_VS_AI and self.game_state.current_player == Player.PLAYER2:
                        return
                    
                    # Select cell and wait for direction
                    self.selected_cell = cell_index
                    self.waiting_for_direction = True

    def handle_direction_key(self, direction):
        """Handle direction selection via keyboard"""
        if not self.waiting_for_direction or self.selected_cell is None:
            return
        
        self.waiting_for_direction = False
        
        stones = self.game_state.board[self.selected_cell]
        if stones > 0:
            self.start_animation(self.selected_cell, direction, self.finish_move)
        else:
            # Redistribute stones
            self.game_state._redistribute_stones()
            # Switch turn
            self.game_state.current_player = Player.PLAYER2 if self.game_state.current_player == Player.PLAYER1 else Player.PLAYER1
        
        self.selected_cell = None

    def execute_move(self, cell_index, direction):
        """Execute a move with the chosen direction"""
        stones = self.game_state.board[cell_index]
        if stones > 0:
            self.start_animation(cell_index, direction, self.finish_move)
        else:
            self.game_state._redistribute_stones()

    def finish_move(self, last_position):
        # Get positions to capture
        capture_positions = self.game_state._capture_stones_correct(last_position, self.animation.direction)
        
        # Start capture animation if there are positions to capture
        if capture_positions:
            self.start_capture_animation(capture_positions, self.finish_turn)
        else:
            self.finish_turn(None)

    def finish_turn(self, _):
        """Called after all animations finish - handles turn switching"""
        self.game_state._check_game_over()
        
        if not self.game_state.game_over:
            # Switch turns
            self.game_state.current_player = Player.PLAYER2 if self.game_state.current_player == Player.PLAYER1 else Player.PLAYER1
            
            # AI move
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
            best_move, best_direction = self.ai_engine.get_best_move(self.game_state)
            if best_move is not None:
                stones = self.game_state.board[best_move]
                if stones > 0:
                    # AI uses same direction logic as human Player 2 would
                    self.start_animation(best_move, best_direction, self.finish_move)
                else:
                    # AI redistribute stones
                    self.game_state._redistribute_stones()
                    # Switch turn back to human
                    self.game_state.current_player = Player.PLAYER1

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        result_rect = pygame.Rect(WINDOW_WIDTH//2 - 250, WINDOW_HEIGHT//2 - 120, 500, 240)
        pygame.draw.rect(self.screen, (240, 240, 240), result_rect)
        pygame.draw.rect(self.screen, TEXT_COLOR, result_rect, 4)
        
        # Winner text
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
        
        # Score
        score_text = f"Score: {self.game_state.player1_score} - {self.game_state.player2_score}"
        score_surface = self.font.render(score_text, True, TEXT_COLOR)
        score_rect = score_surface.get_rect(center=(result_rect.centerx, result_rect.centery))
        self.screen.blit(score_surface, score_rect)
        
        # Instructions
        restart_text = "Press R to restart"
        menu_text = "Press M for main menu"
        
        restart_surface = self.small_font.render(restart_text, True, TEXT_COLOR)
        menu_surface = self.small_font.render(menu_text, True, TEXT_COLOR)
        
        restart_rect = restart_surface.get_rect(center=(result_rect.centerx, result_rect.centery + 40))
        menu_rect = menu_surface.get_rect(center=(result_rect.centerx, result_rect.centery + 65))
        
        self.screen.blit(restart_surface, restart_rect)
        self.screen.blit(menu_surface, menu_rect)

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
                            # Get cell rects and handle click immediately
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
                        # Direction depends on current player
                        if self.game_state.current_player == Player.PLAYER1:
                            self.handle_direction_key(Direction.COUNTER_CLOCKWISE)
                        else:  # Player 2 - reverse direction
                            self.handle_direction_key(Direction.CLOCKWISE)
                    elif event.key == pygame.K_RIGHT:
                        # Direction depends on current player  
                        if self.game_state.current_player == Player.PLAYER1:
                            self.handle_direction_key(Direction.CLOCKWISE)
                        else:  # Player 2 - reverse direction
                            self.handle_direction_key(Direction.COUNTER_CLOCKWISE)
            
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

    def get_cell_rects(self):
        """Get cell rectangles for click detection"""
        cell_width, cell_height = 120, 90
        start_x, start_y = 180, 250
        cell_rects = {}
        
        # Top row (Player 2)
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y
            cell_index = 5 - i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            cell_rects[cell_index] = rect
        
        # Bottom row (Player 1)
        for i in range(5):
            x = start_x + i * (cell_width + 10)
            y = start_y + cell_height + 70
            cell_index = 7 + i
            rect = pygame.Rect(x, y, cell_width, cell_height)
            cell_rects[cell_index] = rect
        
        return cell_rects

if __name__ == "__main__":
    game = OAnQuanGame()
    game.run()
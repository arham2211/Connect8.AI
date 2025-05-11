import pygame
import numpy as np
import random
import math
import sys
import time
from pygame import gfxdraw
import threading

# Initialize Pygame
pygame.init()

# Default Game Constants
DEFAULT_ROWS = 10
DEFAULT_COLS = 16
SQUARE_SIZE = 50  # Reduced from 60 to fit laptop screen
RADIUS = int(SQUARE_SIZE / 2 - 5)
BOARD_COLOR = (0, 32, 77)  # Darker blue to match the image
DARK_BLUE = (0, 32, 77)  # For backgrounds
BG_COLOR = (0, 32, 77)
BLACK = (0, 0, 0)
RED = (220, 57, 46)  # Red
YELLOW = (255, 215, 0)  # Brighter yellow
WHITE = (255, 255, 255)
GREEN = (0, 200, 0)  # Bright green for buttons
BLUE = (33, 150, 243)  # Blue
DARK_GRAY = (66, 66, 66)
LIGHT_GRAY = (224, 224, 224)
LIGHT_BLUE = (80, 150, 255)
LIGHT_GREEN = (144, 238, 144)  # Light green for column hover
PURPLE = (148, 0, 211)  # Purple for gravity off mode

# Animation Constants
DROP_ANIMATION_SPEED = 20  # Speed of piece dropping animation

# Load fonts
pygame.font.init()
FONT = pygame.font.SysFont('Arial', 18)
MEDIUM_FONT = pygame.font.SysFont('Arial', 24)
LARGE_FONT = pygame.font.SysFont('Arial', 36)
TITLE_FONT = pygame.font.SysFont('Arial', 48, bold=True)  # Reduced from 60 to fit better

# Game Settings
CONNECT_N = 8  # Default, always 8 now
GRAVITY_MODE = True
MAX_AI_THINK_TIME = 3.0

# Global variables for board dimensions
ROWS = DEFAULT_ROWS
COLS = DEFAULT_COLS
WIDTH = COLS * SQUARE_SIZE
HEIGHT = (ROWS + 1) * SQUARE_SIZE + 100  # Extra space for UI elements

# Initialize screen with default dimensions
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Connect8.AI')

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, DARK_GRAY, self.rect, 2, border_radius=10)
        
        text_surf = MEDIUM_FONT.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

class InputBox:
    def __init__(self, x, y, width, height, text='', label=''):
        self.rect = pygame.Rect(x, y, width, height)
        self.color_inactive = LIGHT_GRAY
        self.color_active = LIGHT_BLUE
        self.color = self.color_inactive
        self.text = text
        self.label = label
        self.label_surface = MEDIUM_FONT.render(label, True, WHITE)
        self.txt_surface = MEDIUM_FONT.render(text, True, BLACK)
        self.active = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable
                self.active = not self.active
            else:
                self.active = False
            # Change the current color
            self.color = self.color_active if self.active else self.color_inactive
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = self.color_inactive
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    # Only accept numbers
                    if event.unicode.isdigit():
                        self.text += event.unicode
                # Re-render the text
                self.txt_surface = MEDIUM_FONT.render(self.text, True, BLACK)
                
    def update(self):
        # Resize the box if the text is too long
        width = max(200, self.txt_surface.get_width() + 10)
        self.rect.w = width
        
    def draw(self, screen):
        # Draw label
        screen.blit(self.label_surface, (self.rect.x, self.rect.y - 30))
        # Draw the rect
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        # Draw the text
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))

class PowerUp:
    def __init__(self, type_name, color, active=False):
        self.type = type_name
        self.color = color
        self.active = active
        
    def activate(self):
        self.active = True
        
    def deactivate(self):
        self.active = False

class AnimatedPiece:
    def __init__(self, col, row, piece, start_y=0):
        self.col = col
        self.target_row = row
        self.current_y = start_y
        self.piece = piece
        self.done = False
        
    def update(self):
        target_y = (self.target_row + 1) * SQUARE_SIZE + SQUARE_SIZE / 2
        if self.current_y < target_y:
            self.current_y += DROP_ANIMATION_SPEED
            if self.current_y >= target_y:
                self.current_y = target_y
                self.done = True
        else:
            self.done = True
            
    def draw(self, screen):
        x = int(self.col * SQUARE_SIZE + SQUARE_SIZE / 2)
        y = int(self.current_y)
        
        if self.piece == 1:  # Player piece (red)
            pygame.draw.circle(screen, RED, (x, y), RADIUS)
            # Add small dot in center for decoration
            pygame.draw.circle(screen, (255, 150, 150), (x, y), RADIUS//6)
        elif self.piece == 2:  # AI piece (yellow)
            pygame.draw.circle(screen, YELLOW, (x, y), RADIUS)
            # Add small dot in center for decoration
            pygame.draw.circle(screen, (255, 240, 150), (x, y), RADIUS//6)

class Connect8Game:
    def __init__(self):
        global ROWS, COLS, CONNECT_N
        self.board = np.zeros((ROWS, COLS))
        self.turn = 0  # 0 for player, 1 for AI
        self.game_over = False
        self.winner = None
        self.player_powerups = {
            'column_remover': PowerUp('column_remover', GREEN, False),
            'gravity_off': PowerUp('gravity_off', PURPLE, False)
        }
        self.ai_powerups = {
            'column_remover': PowerUp('column_remover', GREEN, False),
            'gravity_off': PowerUp('gravity_off', PURPLE, False)
        }
        self.ai_difficulty = 'easy'  # Default to easy
        self.gravity_mode = GRAVITY_MODE
        self.player_piece = 1
        self.ai_piece = 2
        self.last_move = None
        self.powerup_probability = 0.15  # 15% chance to get a powerup after a move
        self.ai_thinking = False
        self.ai_move = None
        self.animated_pieces = []
        self.column_remover_active = False
        self.gravity_off_active = False
        self.hovered_column = -1
        self.hovered_row = -1
        self.powerup_notification = None
        self.powerup_notification_time = 0
        self.switch_to_ai_after_animation = False
        self.switch_to_player_after_animation = False
        self.lock_player_input = False  # Add a lock to prevent player moves during AI turn
        self.ai_thinking_start_time = 0  # Track when AI started thinking
        self.connect_n = CONNECT_N
        
    def reset_game(self):
        global ROWS, COLS
        self.board = np.zeros((ROWS, COLS))
        self.turn = 0
        self.game_over = False
        self.winner = None
        self.last_move = None
        self.ai_thinking = False
        self.ai_move = None
        self.animated_pieces = []
        self.column_remover_active = False
        self.gravity_off_active = False
        self.hovered_column = -1
        self.hovered_row = -1
        self.powerup_notification = None
        self.powerup_notification_time = 0
        self.switch_to_ai_after_animation = False
        self.switch_to_player_after_animation = False
        self.lock_player_input = False
        self.ai_thinking_start_time = 0
        self.player_powerups = {
            'column_remover': PowerUp('column_remover', GREEN, False),
            'gravity_off': PowerUp('gravity_off', PURPLE, False)
        }
        self.ai_powerups = {
            'column_remover': PowerUp('column_remover', GREEN, False),
            'gravity_off': PowerUp('gravity_off', PURPLE, False)
        }
        
    def toggle_gravity_mode(self):
        self.gravity_mode = not self.gravity_mode
        self.reset_game()
        
    def set_difficulty(self, difficulty):
        self.ai_difficulty = difficulty
        self.reset_game()
        
    def drop_piece(self, col, piece, row=None, animate=True):
        if row is not None:  # Direct placement (gravity off mode)
            if self.board[row][col] == 0:
                if animate:
                    # Create animated piece with specific row target
                    self.animated_pieces.append(AnimatedPiece(col, row, piece, (row + 1) * SQUARE_SIZE - SQUARE_SIZE / 2))
                    self.last_move = (row, col)
                    return True, row
                else:
                    # Immediate placement without animation
                    self.board[row][col] = piece
                    self.last_move = (row, col)
                    return True, row
            return False, -1
        elif self.gravity_mode:
            # Standard mode - piece falls to bottom
            for row in range(ROWS-1, -1, -1):
                if self.board[row][col] == 0:
                    if animate:
                        # Create animated piece and don't update the board yet
                        self.animated_pieces.append(AnimatedPiece(col, row, piece, SQUARE_SIZE / 2))
                        self.last_move = (row, col)
                        return True, row
                    else:
                        # Immediate placement without animation
                        self.board[row][col] = piece
                        self.last_move = (row, col)
                        return True, row
            return False, -1
        else:
            # Gravity-free mode - piece stays where placed
            for row in range(ROWS-1, -1, -1):
                if self.board[row][col] == 0:
                    if animate:
                        # Create animated piece and don't update the board yet
                        self.animated_pieces.append(AnimatedPiece(col, row, piece, SQUARE_SIZE / 2))
                        self.last_move = (row, col)
                        return True, row
                    else:
                        # Immediate placement without animation
                        self.board[row][col] = piece
                        self.last_move = (row, col)
                        return True, row
            return False, -1
    
    def update_animations(self):
        # Update all animated pieces
        for piece in self.animated_pieces[:]:
            piece.update()
            if piece.done:
                # When animation is done, update the board
                if 0 <= piece.target_row < ROWS and 0 <= piece.col < COLS:
                    self.board[piece.target_row][piece.col] = piece.piece
                    
                    # Check for win immediately after the piece lands and updates the board
                    if self.check_win(piece.piece):
                        self.game_over = True
                        self.winner = 1 if piece.piece == self.player_piece else 2
                        
                self.animated_pieces.remove(piece)
                
    def is_valid_location(self, col, row=None):
        # For gravity_off mode, check if specific cell is valid
        if row is not None:
            return 0 <= row < ROWS and 0 <= col < COLS and self.board[row][col] == 0
        
        # For regular mode, check if column has space
        return col >= 0 and col < COLS and self.board[0][col] == 0
        
    def get_valid_locations(self):
        # For regular mode
        valid_locations = []
        for col in range(COLS):
            if self.is_valid_location(col):
                valid_locations.append(col)
        return valid_locations
    
    def get_valid_cells(self):
        # For gravity off mode, return all empty cells as (row, col) tuples
        valid_cells = []
        for row in range(ROWS):
            for col in range(COLS):
                if self.board[row][col] == 0:
                    valid_cells.append((row, col))
        return valid_cells
    
    def is_column_empty(self, col):
        """Check if a column is completely empty"""
        for row in range(ROWS):
            if self.board[row][col] != 0:
                return False
        return True
    
    def remove_column(self, col):
        """Remove all pieces from a column"""
        if 0 <= col < COLS:
            for row in range(ROWS):
                self.board[row][col] = 0
            return True
        return False
    
    def use_powerup(self, powerup_type, col=None, row=None):
        powerups = self.player_powerups if self.turn == 0 else self.ai_powerups
        
        if powerup_type == 'column_remover' and powerups['column_remover'].active:
            if col is not None and 0 <= col < COLS:
                success = self.remove_column(col)
                if success:
                    powerups['column_remover'].deactivate()
                    return True
        elif powerup_type == 'gravity_off' and powerups['gravity_off'].active:
            # When activated, this will be handled in the main game logic
            # The deactivation happens after a piece is placed
            return True
        
        return False
    
    def check_for_powerup(self):
        if random.random() < self.powerup_probability:
            # Randomly choose between column remover and gravity off
            powerup_type = random.choice(['column_remover', 'gravity_off'])
            powerups = self.player_powerups if self.turn == 0 else self.ai_powerups
            powerups[powerup_type].activate()
            
            # Set notification
            player_type = "Player" if self.turn == 0 else "AI"
            powerup_name = "Column Remover" if powerup_type == 'column_remover' else "Gravity Off"
            self.powerup_notification = f"{player_type} got a {powerup_name}"
            self.powerup_notification_time = time.time()
            
            return True, powerup_type
        return False, None
    
    def check_win(self, piece):
        # Check horizontal
        for r in range(ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [self.board[r][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check vertical
        for c in range(COLS):
            for r in range(ROWS - self.connect_n + 1):
                window = [self.board[r+i][c] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check diagonal (positive slope)
        for r in range(ROWS - self.connect_n + 1):
            for c in range(COLS - self.connect_n + 1):
                window = [self.board[r+i][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check diagonal (negative slope)
        for r in range(self.connect_n - 1, ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [self.board[r-i][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
    
        return False
    
    def is_terminal_node(self):
        return self.check_win(self.player_piece) or self.check_win(self.ai_piece) or len(self.get_valid_locations()) == 0
    
    def evaluate_window(self, window, piece):
        score = 0
        opp_piece = self.player_piece if piece == self.ai_piece else self.ai_piece
        
        if window.count(piece) == self.connect_n:
            score += 1000000  # Winning move
        elif window.count(piece) == self.connect_n - 1 and window.count(0) == 1:
            score += 50000  # Almost winning (n-1 in a row)
        elif window.count(piece) == self.connect_n - 2 and window.count(0) == 2:
            score += 10000  # n-2 in a row
        elif window.count(piece) == self.connect_n - 3 and window.count(0) == 3:
            score += 1000   # n-3 in a row
        elif window.count(piece) == self.connect_n - 4 and window.count(0) == 4:
            score += 100    # n-4 in a row
        elif window.count(piece) >= 3:
            score += 10     # 3 in a row
        elif window.count(piece) >= 2:
            score += 2      # 2 in a row
            
        if window.count(opp_piece) == self.connect_n - 1 and window.count(0) == 1:
            score -= 50000  # Block opponent's almost win
        elif window.count(opp_piece) == self.connect_n - 2 and window.count(0) == 2:
            score -= 10000  # Block opponent's n-2 in a row
        
        return score
    
    def score_position(self, piece):
        score = 0
        
        # Score center columns
        center_cols = [COLS // 2 - 1, COLS // 2]
        for center_col in center_cols:
            center_array = [int(self.board[r][center_col]) for r in range(ROWS)]
            center_count = center_array.count(piece)
            score += center_count * 3
        
        # Score all possible windows
        # Horizontal windows
        for r in range(ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [int(self.board[r][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Vertical windows
        for c in range(COLS):
            for r in range(ROWS - self.connect_n + 1):
                window = [int(self.board[r+i][c]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Positive diagonal windows
        for r in range(ROWS - self.connect_n + 1):
            for c in range(COLS - self.connect_n + 1):
                window = [int(self.board[r+i][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Negative diagonal windows
        for r in range(self.connect_n - 1, ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [int(self.board[r-i][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        return score
    
    def minimax(self, depth, alpha, beta, maximizing_player, start_time, sim_board):
        # Check if we're out of time
        if time.time() - start_time > MAX_AI_THINK_TIME:
            raise TimeoutError("AI thinking took too long")
        
        # Get valid locations for the simulated board
        valid_locations = []
        for col in range(COLS):
            if col >= 0 and col < COLS and sim_board[0][col] == 0:
                valid_locations.append(col)
        
        # Check for terminal condition in simulated board
        is_terminal = self.check_win_sim(sim_board, self.player_piece) or \
                      self.check_win_sim(sim_board, self.ai_piece) or \
                      len(valid_locations) == 0
        
        if depth == 0 or is_terminal:
            if is_terminal:
                if self.check_win_sim(sim_board, self.ai_piece):
                    return (None, 1000000)
                elif self.check_win_sim(sim_board, self.player_piece):
                    return (None, -1000000)
                else:  # Game is over, no more valid moves
                    return (None, 0)
            else:  # Depth is zero
                return (None, self.score_position_sim(sim_board, self.ai_piece))
        
        if maximizing_player:
            value = -math.inf
            column = random.choice(valid_locations) if valid_locations else None
            
            for col in valid_locations:
                # Make a simulated move using the simulated board
                sim_board_copy = np.copy(sim_board)
                row = self.get_next_open_row(sim_board_copy, col)
                if row != -1:
                    sim_board_copy[row][col] = self.ai_piece
                    new_score = self.minimax(depth-1, alpha, beta, False, start_time, sim_board_copy)[1]
                    
                    if new_score > value:
                        value = new_score
                        column = col
                    alpha = max(alpha, value)
                    if alpha >= beta:
                        break
            return column, value
        
        else:  # Minimizing player
            value = math.inf
            column = random.choice(valid_locations) if valid_locations else None
            
            for col in valid_locations:
                # Make a simulated move using the simulated board
                sim_board_copy = np.copy(sim_board)
                row = self.get_next_open_row(sim_board_copy, col)
                if row != -1:
                    sim_board_copy[row][col] = self.player_piece
                    new_score = self.minimax(depth-1, alpha, beta, True, start_time, sim_board_copy)[1]
                    
                    if new_score < value:
                        value = new_score
                        column = col
                    beta = min(beta, value)
                    if alpha >= beta:
                        break
            return column, value
    
    # Helper functions for simulated board operations
    def check_win_sim(self, board, piece):
        # Check horizontal
        for r in range(ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [board[r][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check vertical
        for c in range(COLS):
            for r in range(ROWS - self.connect_n + 1):
                window = [board[r+i][c] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check diagonal (positive slope)
        for r in range(ROWS - self.connect_n + 1):
            for c in range(COLS - self.connect_n + 1):
                window = [board[r+i][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
        
        # Check diagonal (negative slope)
        for r in range(self.connect_n - 1, ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [board[r-i][c+i] for i in range(self.connect_n)]
                if all(cell == piece for cell in window):
                    return True
    
        return False
    
    def score_position_sim(self, board, piece):
        score = 0
        
        # Score center columns
        center_cols = [COLS // 2 - 1, COLS // 2]
        for center_col in center_cols:
            if center_col < COLS:  # Make sure center column exists
                center_array = [int(board[r][center_col]) for r in range(ROWS)]
                center_count = center_array.count(piece)
                score += center_count * 3
        
        # Score horizontal windows
        for r in range(ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [int(board[r][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Score vertical windows
        for c in range(COLS):
            for r in range(ROWS - self.connect_n + 1):
                window = [int(board[r+i][c]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Score positive diagonal windows
        for r in range(ROWS - self.connect_n + 1):
            for c in range(COLS - self.connect_n + 1):
                window = [int(board[r+i][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        # Score negative diagonal windows
        for r in range(self.connect_n - 1, ROWS):
            for c in range(COLS - self.connect_n + 1):
                window = [int(board[r-i][c+i]) for i in range(self.connect_n)]
                score += self.evaluate_window(window, piece)
        
        return score
    
    def get_next_open_row(self, board, col):
        for row in range(ROWS-1, -1, -1):
            if board[row][col] == 0:
                return row
        return -1
    
    def get_easy_move(self):
        """Easy difficulty: Random valid move"""
        # If gravity off is active, choose a random empty cell
        if self.ai_powerups['gravity_off'].active and random.random() > 0.3:  # 70% chance to use gravity off
            valid_cells = self.get_valid_cells()
            if valid_cells:
                row, col = random.choice(valid_cells)
                return col, row
        
        # Otherwise use regular gravity mode
        valid_locations = self.get_valid_locations()
        if valid_locations:
            return random.choice(valid_locations), None
        return None, None
    
    def get_medium_move(self):
        """Medium difficulty: Minimax with limited depth (3)"""
        # If gravity off is active, use it sometimes
        if self.ai_powerups['gravity_off'].active and random.random() > 0.3:  # 70% chance to use gravity off
            valid_cells = self.get_valid_cells()
            if valid_cells:
                # Try to find strategic places instead of random
                best_cell = None
                best_score = -math.inf
                
                for row, col in valid_cells:
                    # Try placing a piece here
                    sim_board = np.copy(self.board)
                    sim_board[row][col] = self.ai_piece
                    score = self.score_position_sim(sim_board, self.ai_piece)
                    
                    if score > best_score:
                        best_score = score
                        best_cell = (row, col)
                
                if best_cell:
                    return best_cell[1], best_cell[0]  # Return as col, row
            
        try:
            start_time = time.time()
            # Create a simulation board - don't modify the game board
            sim_board = np.copy(self.board)
            col, _ = self.minimax(3, -math.inf, math.inf, True, start_time, sim_board)
            return col, None
        except TimeoutError:
            return self.get_easy_move()
    
    def get_hard_move(self):
        """Hard difficulty: Full Minimax with Alpha-Beta Pruning"""
        # If gravity off is active, use it strategically
        if self.ai_powerups['gravity_off'].active and random.random() > 0.2:  # 80% chance to use gravity off
            valid_cells = self.get_valid_cells()
            if valid_cells:
                best_cell = None
                best_score = -math.inf
                
                # Deeply analyze each possible cell
                for row, col in valid_cells:
                    sim_board = np.copy(self.board)
                    sim_board[row][col] = self.ai_piece
                    
                    # Check if this is a winning move
                    if self.check_win_sim(sim_board, self.ai_piece):
                        return col, row  # Immediate win
                    
                    # Check if this blocks a player win
                    for r, c in valid_cells:
                        if r != row or c != col:  # Don't check the same cell
                            test_board = np.copy(self.board)
                            test_board[r][c] = self.player_piece
                            if self.check_win_sim(test_board, self.player_piece):
                                # This is a critical blocking move
                                return c, r
                    
                    score = self.score_position_sim(sim_board, self.ai_piece)
                    if score > best_score:
                        best_score = score
                        best_cell = (row, col)
                
                if best_cell:
                    return best_cell[1], best_cell[0]  # Return as col, row
        
        try:
            start_time = time.time()
            # Use iterative deepening to ensure we always have a move
            best_col = random.choice(self.get_valid_locations()) if self.get_valid_locations() else None
            
            # Create a simulation board - don't modify the game board
            sim_board = np.copy(self.board)
            
            for current_depth in range(1, 6):  # Up to depth 5
                try:
                    col, score = self.minimax(current_depth, -math.inf, math.inf, True, start_time, sim_board)
                    if col is not None:
                        best_col = col
                    
                    # If we're running out of time, stop deepening
                    if time.time() - start_time > MAX_AI_THINK_TIME * 0.8:
                        break
                except TimeoutError:
                    break
            
            return best_col, None
        except TimeoutError:
            return self.get_medium_move()
    
    def ai_think_thread(self):
        """Separate thread for AI thinking to prevent UI freezing"""
        try:
            self.ai_thinking_start_time = time.time()
            
            # Check if AI should use column remover powerup
            if self.ai_powerups['column_remover'].active and random.random() > 0.5:
                # Find a column with opponent pieces to remove
                opponent_columns = []
                for col in range(COLS):
                    for row in range(ROWS):
                        if self.board[row][col] == self.player_piece:
                            opponent_columns.append(col)
                            break
                
                if opponent_columns:
                    col = random.choice(opponent_columns)
                    self.use_powerup('column_remover', col)
                    self.ai_move = None, None  # AI used powerup
                    return
            
            # Make a regular move or use gravity off
            if self.ai_difficulty == 'easy':
                self.ai_move = self.get_easy_move()
            elif self.ai_difficulty == 'medium':
                self.ai_move = self.get_medium_move()
            elif self.ai_difficulty == 'hard':
                self.ai_move = self.get_hard_move()
            else:
                self.ai_move = self.get_easy_move()  # Fallback
            
        except Exception as e:
            print(f"AI thinking error: {e}")
            # Fallback to random move if there's an error
            valid_locations = self.get_valid_locations()
            if valid_locations:
                self.ai_move = random.choice(valid_locations), None
            else:
                self.ai_move = None, None  # No valid moves
        finally:
            self.ai_thinking = False
    
    def draw_board(self, screen):
        # Draw the board background
        pygame.draw.rect(screen, BOARD_COLOR, (0, SQUARE_SIZE, WIDTH, ROWS * SQUARE_SIZE))
        
        # Draw column hover effect when column remover is active
        if self.column_remover_active and 0 <= self.hovered_column < COLS:
            column_surface = pygame.Surface((SQUARE_SIZE, ROWS * SQUARE_SIZE), pygame.SRCALPHA)
            column_surface.fill((0, 255, 0, 50))  # Light green with transparency
            screen.blit(column_surface, (self.hovered_column * SQUARE_SIZE, SQUARE_SIZE))
            
            # Draw removal button at the bottom of the column
            button_y = (ROWS + 1) * SQUARE_SIZE
            button_rect = pygame.Rect(self.hovered_column * SQUARE_SIZE, button_y, SQUARE_SIZE, 30)
            pygame.draw.rect(screen, GREEN, button_rect, border_radius=5)
            pygame.draw.rect(screen, WHITE, button_rect, 1, border_radius=5)
            
            remove_text = FONT.render("✖", True, WHITE)
            text_rect = remove_text.get_rect(center=button_rect.center)
            screen.blit(remove_text, text_rect)
        
        # Draw cell hover effect when gravity off mode is active
        if self.gravity_off_active and 0 <= self.hovered_row < ROWS and 0 <= self.hovered_column < COLS:
            if self.board[self.hovered_row][self.hovered_column] == 0:  # Only highlight empty cells
                cell_rect = pygame.Rect(
                    self.hovered_column * SQUARE_SIZE, 
                    (self.hovered_row + 1) * SQUARE_SIZE, 
                    SQUARE_SIZE, SQUARE_SIZE
                )
                cell_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                cell_surface.fill((148, 0, 211, 80))  # Purple with transparency
                screen.blit(cell_surface, cell_rect)
        
        # Draw circles for empty spots and pieces
        for c in range(COLS):
            for r in range(ROWS):
                # Calculate center position
                x = int(c * SQUARE_SIZE + SQUARE_SIZE / 2)
                y = int((r + 1) * SQUARE_SIZE + SQUARE_SIZE / 2)
                
                # Draw pieces with a clean look matching the image
                if self.board[r][c] == 0:  # Empty spot - blue circle
                    pygame.draw.circle(screen, BLUE, (x, y), RADIUS)
                    
                elif self.board[r][c] == 1:  # Player piece (red)
                    pygame.draw.circle(screen, RED, (x, y), RADIUS)
                    # Add small dot in center for decoration as in the image
                    pygame.draw.circle(screen, (255, 150, 150), (x, y), RADIUS//6)
                    
                elif self.board[r][c] == 2:  # AI piece (yellow)
                    pygame.draw.circle(screen, YELLOW, (x, y), RADIUS)
                    # Add small dot in center for decoration as in the image
                    pygame.draw.circle(screen, (255, 240, 150), (x, y), RADIUS//6)
        
        # Draw animated pieces
        for piece in self.animated_pieces:
            piece.draw(screen)
                
        # Highlight the last move with a subtle indicator
        if self.last_move and not self.animated_pieces:
            r, c = self.last_move
            x = int(c * SQUARE_SIZE + SQUARE_SIZE / 2)
            y = int((r + 1) * SQUARE_SIZE + SQUARE_SIZE / 2)
            pygame.draw.circle(screen, WHITE, (x, y), RADIUS + 3, 2)
    
    def draw_hover_piece(self, screen, col, row=None):
        if self.gravity_off_active and row is not None:
            # Gravity off mode - show piece at mouse hover position
            if 0 <= col < COLS and 0 <= row < ROWS and self.board[row][col] == 0:
                x = int(col * SQUARE_SIZE + SQUARE_SIZE / 2)
                y = int((row + 1) * SQUARE_SIZE + SQUARE_SIZE / 2)
                piece_color = RED if self.turn == 0 else YELLOW
                # Draw with transparency for hover effect
                s = pygame.Surface((RADIUS*2+4, RADIUS*2+4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*pygame.Color(piece_color)[:3], 180), (RADIUS+2, RADIUS+2), RADIUS)
                screen.blit(s, (x-RADIUS-2, y-RADIUS-2))
        elif 0 <= col < COLS and not self.game_over and not self.column_remover_active and not self.lock_player_input:
            # Regular mode - show piece at top of column
            x = int(col * SQUARE_SIZE + SQUARE_SIZE / 2)
            piece_color = RED if self.turn == 0 else YELLOW
            # Draw with transparency for hover effect
            s = pygame.Surface((RADIUS*2+4, RADIUS*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*pygame.Color(piece_color)[:3], 180), (RADIUS+2, RADIUS+2), RADIUS)
            screen.blit(s, (x-RADIUS-2, SQUARE_SIZE//2-RADIUS-2))
    
    def draw_notification(self, screen):
        # Display powerup notification with simple styling in the top-left corner
        if self.powerup_notification and time.time() - self.powerup_notification_time < 3.0:
            # Draw a small notification in top-left
            notif_text = FONT.render(self.powerup_notification, True, GREEN)
            screen.blit(notif_text, (10, 10))
    
    def draw_powerups(self, screen):
        # Background for powerups area
        pygame.draw.rect(screen, DARK_BLUE, (0, HEIGHT - 100, WIDTH, 100))
        
        # Show compact game info at bottom
        title_text = LARGE_FONT.render(f"CONNECT {self.connect_n}", True, WHITE)
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT - 80))
        
        # Show powerup status with improved styling - Column Remover
        if self.player_powerups['column_remover'].active:
            # Create a styled button/banner for the powerup
            powerup_rect = pygame.Rect(20, HEIGHT - 70, 150, 50)
            pygame.draw.rect(screen, (0, 100, 0), powerup_rect, border_radius=10)  # Dark green background
            pygame.draw.rect(screen, GREEN, powerup_rect, 2, border_radius=10)  # Bright green border
            
            # Text with shadow for better visibility
            powerup_text = MEDIUM_FONT.render("Column Remover", True, WHITE)
            screen.blit(powerup_text, (powerup_rect.centerx - powerup_text.get_width() // 2, 
                                      powerup_rect.y + 8))
            
            if not self.column_remover_active:
                # Create button for activation
                activate_rect = pygame.Rect(20, HEIGHT - 30, 150, 25)
                pygame.draw.rect(screen, (0, 150, 0), activate_rect, border_radius=8)
                
                activate_text = FONT.render("Activate", True, WHITE)
                screen.blit(activate_text, (activate_rect.centerx - activate_text.get_width() // 2, 
                                          activate_rect.y + 4))
                
                # Store the activation button rect for click detection
                self.column_remover_button_rect = activate_rect
            else:
                # Create button for deactivation
                deactivate_rect = pygame.Rect(20, HEIGHT - 30, 150, 25)
                pygame.draw.rect(screen, (150, 0, 0), deactivate_rect, border_radius=8)
                
                deactivate_text = FONT.render("Cancel", True, WHITE)
                screen.blit(deactivate_text, (deactivate_rect.centerx - deactivate_text.get_width() // 2, 
                                            deactivate_rect.y + 4))
                
                # Store the deactivation button rect
                self.column_remover_button_rect = deactivate_rect
        
        # Show powerup status - Gravity Off
        if self.player_powerups['gravity_off'].active:
            # Create a styled button/banner for the powerup
            powerup_rect = pygame.Rect(180, HEIGHT - 70, 150, 50)
            pygame.draw.rect(screen, (70, 0, 120), powerup_rect, border_radius=10)  # Dark purple background
            pygame.draw.rect(screen, PURPLE, powerup_rect, 2, border_radius=10)  # Bright purple border
            
            # Text for better visibility
            powerup_text = MEDIUM_FONT.render("Gravity Off", True, WHITE)
            screen.blit(powerup_text, (powerup_rect.centerx - powerup_text.get_width() // 2, 
                                      powerup_rect.y + 8))
            
            if not self.gravity_off_active:
                # Create button for activation
                activate_rect = pygame.Rect(180, HEIGHT - 30, 150, 25)
                pygame.draw.rect(screen, (100, 0, 180), activate_rect, border_radius=8)
                
                activate_text = FONT.render("Activate", True, WHITE)
                screen.blit(activate_text, (activate_rect.centerx - activate_text.get_width() // 2, 
                                          activate_rect.y + 4))
                
                # Store the activation button rect for click detection
                self.gravity_off_button_rect = activate_rect
            else:
                # Create button for deactivation
                deactivate_rect = pygame.Rect(180, HEIGHT - 30, 150, 25)
                pygame.draw.rect(screen, (150, 0, 0), deactivate_rect, border_radius=8)
                
                deactivate_text = FONT.render("Cancel", True, WHITE)
                screen.blit(deactivate_text, (deactivate_rect.centerx - deactivate_text.get_width() // 2, 
                                            deactivate_rect.y + 4))
                
                # Store the deactivation button rect
                self.gravity_off_button_rect = deactivate_rect
        
        # Show FPS and AI level
        fps_text = FONT.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
        ai_level_text = FONT.render(f"AI Level: {self.ai_difficulty.capitalize()}", True, WHITE)
        screen.blit(fps_text, (WIDTH - fps_text.get_width() - 20, HEIGHT - 60))
        screen.blit(ai_level_text, (WIDTH - ai_level_text.get_width() - 20, HEIGHT - 30))
    
    def draw_game_status(self, screen):
        # Draw top bar
        pygame.draw.rect(screen, DARK_BLUE, (0, 0, WIDTH, SQUARE_SIZE))
        
        status_text = ""
        
        if self.game_over:
            if self.winner == 1:
                status_text = "You Win!"
                text_color = RED
            elif self.winner == 2:
                status_text = "AI Wins!"
                text_color = YELLOW
            else:
                status_text = "Draw!"
                text_color = BLUE
        else:
            if self.turn == 0:
                status_text = "YOUR TURN"
                text_color = (220, 50, 100)  # Pinkish red
            else:
                # If AI is thinking, show a small indicator in the top-left
                if self.ai_thinking:
                    ai_thinking_text = FONT.render("AI thinking...", True, WHITE)
                    screen.blit(ai_thinking_text, (10, 40))
                    
                    # Calculate thinking time
                    thinking_time = time.time() - self.ai_thinking_start_time
                    time_text = FONT.render(f"Time: {thinking_time:.1f}s", True, WHITE)
                    screen.blit(time_text, (10, 60))
                
                status_text = "AI's TURN"
                text_color = YELLOW
        
        text_surface = LARGE_FONT.render(status_text, True, text_color)
        text_rect = text_surface.get_rect(center=(WIDTH // 2, SQUARE_SIZE // 2))
        screen.blit(text_surface, text_rect)
        
        # Draw instructions for column remover if active
        if self.column_remover_active:
            instructions = MEDIUM_FONT.render("Hover over a column to remove it", True, GREEN)
            screen.blit(instructions, (WIDTH // 2 - instructions.get_width() // 2, 20))
        
        # Draw instructions for gravity off if active
        if self.gravity_off_active:
            instructions = MEDIUM_FONT.render("Click anywhere on the board to place your piece", True, PURPLE)
            screen.blit(instructions, (WIDTH // 2 - instructions.get_width() // 2, 20))
        
        # Draw notification for powerups
        self.draw_notification(screen)

def show_game_over_screen(winner):
    """
    Display a game over screen showing who won and options to play again or exit
    """
    game_over = True
    
    # Create buttons
    button_width = 250
    button_height = 50
    spacing = 20
    start_y = HEIGHT//2 + 50
    
    play_again_button = Button(WIDTH//2 - button_width//2, start_y, button_width, button_height, "Play Again", GREEN, (0, 180, 0), WHITE)
    exit_button = Button(WIDTH//2 - button_width//2, start_y + button_height + spacing, button_width, button_height, "Exit to Menu", RED, (180, 40, 40), WHITE)
    
    while game_over:
        screen.fill(DARK_BLUE)
        
        # Draw winner announcement
        if winner == 1:
            title_text = TITLE_FONT.render("YOU WIN!", True, RED)
            subtitle_text = LARGE_FONT.render("Congratulations! You defeated the AI.", True, WHITE)
        elif winner == 2:
            title_text = TITLE_FONT.render("AI WINS!", True, YELLOW)
            subtitle_text = LARGE_FONT.render("Better luck next time!", True, WHITE)
        else:
            title_text = TITLE_FONT.render("DRAW!", True, WHITE)
            subtitle_text = LARGE_FONT.render("It's a tie! No one wins.", True, LIGHT_BLUE)
        
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//4))
        screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, HEIGHT//4 + 80))
        
        mouse_pos = pygame.mouse.get_pos()
        
        play_again_button.check_hover(mouse_pos)
        play_again_button.draw(screen)
        
        exit_button.check_hover(mouse_pos)
        exit_button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_again_button.is_clicked(mouse_pos, event):
                    return True  # Play again
                    
                elif exit_button.is_clicked(mouse_pos, event):
                    return False  # Exit to menu
        
        pygame.display.update()
        clock.tick(60)

def custom_grid_menu():
    """
    Menu for selecting custom grid dimensions and connect-n value
    """
    global ROWS, COLS, CONNECT_N, WIDTH, HEIGHT, screen
    
    screen.fill(DARK_BLUE)
    
    menu = True
    
    # Create input boxes
    rows_input = InputBox(WIDTH//2 - 100, HEIGHT//2 - 120, 200, 40, str(ROWS), 'Number of Rows (10-19):')
    cols_input = InputBox(WIDTH//2 - 100, HEIGHT//2, 200, 40, str(COLS), 'Number of Columns (16-23):')
    
    # Create buttons
    button_width = 250
    button_height = 50
    spacing = 20
    start_y = HEIGHT//2 + 200
    
    save_button = Button(WIDTH//2 - button_width//2, start_y, button_width, button_height, "Save Settings", GREEN, (0, 180, 0), WHITE)
    cancel_button = Button(WIDTH//2 - button_width//2, start_y + button_height + spacing, button_width, button_height, "Cancel", RED, (180, 40, 40), WHITE)
    
    # Adjust title position
    title_y = 50
    
    while menu:
        screen.fill(DARK_BLUE)
        
        # Draw titles
        title_text = TITLE_FONT.render("CUSTOM GRID SETTINGS", True, WHITE)
        subtitle_text = MEDIUM_FONT.render("Customize your game board dimensions", True, LIGHT_BLUE)
        
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, title_y))
        screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, title_y + 70))
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            # Handle input box events for rows and cols only
            rows_input.handle_event(event)
            cols_input.handle_event(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if save_button.is_clicked(mouse_pos, event):
                    try:
                        # Get values from input boxes
                        new_rows = int(rows_input.text)
                        new_cols = int(cols_input.text)
                        
                        # Validate inputs with new minimum values
                        new_rows = max(10, min(19, new_rows))  # Min 10, max 19 rows
                        new_cols = max(16, min(23, new_cols))  # Min 16, max 23 columns
                        
                        # Apply new settings
                        ROWS = new_rows
                        COLS = new_cols
                        
                        # Update screen dimensions
                        WIDTH = COLS * SQUARE_SIZE
                        HEIGHT = (ROWS + 1) * SQUARE_SIZE + 100
                        
                        # Resize the screen
                        screen = pygame.display.set_mode((WIDTH, HEIGHT))
                        pygame.display.set_caption('Connect8.AI')
                        
                        return
                    except ValueError:
                        # Show error message if inputs are invalid
                        error_text = MEDIUM_FONT.render("Please enter valid numbers", True, RED)
                        screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//2 + 260))
                        pygame.display.update()
                        pygame.time.wait(1000)
                
                elif cancel_button.is_clicked(mouse_pos, event):
                    return
        
        # Update input boxes
        rows_input.update()
        cols_input.update()
        
        # Draw input boxes
        rows_input.draw(screen)
        cols_input.draw(screen)
        
        mouse_pos = pygame.mouse.get_pos()
        
        save_button.check_hover(mouse_pos)
        save_button.draw(screen)
        
        cancel_button.check_hover(mouse_pos)
        cancel_button.draw(screen)
        
        pygame.display.update()
        clock.tick(60)

def main_menu():
    screen.fill(DARK_BLUE)
    
    menu = True
    
    # Adjust button positions and sizes to fit screen better
    button_width = 250  # Reduced from 300
    button_height = 50  # Reduced from 60
    spacing = 20  # Space between buttons
    start_y = HEIGHT//2 - 60  # Start buttons higher up the screen
    
    difficulty_buttons = [
        Button(WIDTH//2 - button_width//2, start_y, button_width, button_height, "Easy", RED, (180, 40, 40), WHITE),
        Button(WIDTH//2 - button_width//2, start_y + button_height + spacing, button_width, button_height, "Medium", (60, 60, 60), (80, 80, 80), WHITE),
        Button(WIDTH//2 - button_width//2, start_y + 2*(button_height + spacing), button_width, button_height, "Hard", (60, 60, 60), (80, 80, 80), WHITE)
    ]
    
    custom_grid_button = Button(WIDTH//2 - button_width//2, start_y + 3*(button_height + spacing), button_width, button_height, "Custom Grid", (60, 60, 60), (80, 80, 80), WHITE)
    start_button = Button(WIDTH//2 - button_width//2, start_y + 4*(button_height + spacing), button_width, button_height, "Start Game", GREEN, (0, 180, 0), WHITE)
    
    selected_difficulty = "easy"
    
    # Adjust title position
    title_y = 50  # Move title up
    
    while menu:
        screen.fill(DARK_BLUE)
        
        # Draw titles with adjusted font size and position
        title_text = TITLE_FONT.render("CONNECT 8", True, WHITE)
        subtitle_text = MEDIUM_FONT.render("A Strategic Board Game with Adaptive AI", True, LIGHT_BLUE)
        
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, title_y))
        screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, title_y + 60))
        
        # Draw section headers
        difficulty_text = LARGE_FONT.render("Select Difficulty:", True, WHITE)
        screen.blit(difficulty_text, (WIDTH//2 - difficulty_text.get_width()//2, start_y - 50))
        
        # Display grid size info
        grid_info = MEDIUM_FONT.render(f"Grid Size: {ROWS}x{COLS}", True, LIGHT_BLUE)
        screen.blit(grid_info, (WIDTH//2 - grid_info.get_width()//2, start_y - 110))
        
        mouse_pos = pygame.mouse.get_pos()
        
        for btn in difficulty_buttons:
            btn.check_hover(mouse_pos)
            btn.draw(screen)
            
        custom_grid_button.check_hover(mouse_pos)
        custom_grid_button.draw(screen)
        
        start_button.check_hover(mouse_pos)
        start_button.draw(screen)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if difficulty_buttons[0].is_clicked(mouse_pos, event):
                    selected_difficulty = "easy"
                    # Update button colors to show selection
                    difficulty_buttons[0].color = RED
                    difficulty_buttons[1].color = (60, 60, 60)
                    difficulty_buttons[2].color = (60, 60, 60)
                    
                elif difficulty_buttons[1].is_clicked(mouse_pos, event):
                    selected_difficulty = "medium"
                    # Update button colors to show selection
                    difficulty_buttons[0].color = (60, 60, 60)
                    difficulty_buttons[1].color = RED
                    difficulty_buttons[2].color = (60, 60, 60)
                    
                elif difficulty_buttons[2].is_clicked(mouse_pos, event):
                    selected_difficulty = "hard"
                    # Update button colors to show selection
                    difficulty_buttons[0].color = (60, 60, 60)
                    difficulty_buttons[1].color = (60, 60, 60)
                    difficulty_buttons[2].color = RED
                
                elif custom_grid_button.is_clicked(mouse_pos, event):
                    custom_grid_menu()
                    # After returning from custom grid menu, resize buttons if needed
                    start_y = HEIGHT//2 - 60
                    
                    for i, btn in enumerate(difficulty_buttons):
                        btn.rect.y = start_y + i * (button_height + spacing)
                        btn.rect.x = WIDTH//2 - button_width//2
                    
                    custom_grid_button.rect.y = start_y + 3 * (button_height + spacing)
                    custom_grid_button.rect.x = WIDTH//2 - button_width//2
                    
                    start_button.rect.y = start_y + 4 * (button_height + spacing)
                    start_button.rect.x = WIDTH//2 - button_width//2
                    
                elif start_button.is_clicked(mouse_pos, event):
                    # Start the game after a short delay
                    pygame.time.wait(300)
                    return selected_difficulty, True  # Always use gravity mode
        
        pygame.display.update()

def play_game():
    global ROWS, COLS, CONNECT_N, WIDTH, HEIGHT, screen
    
    difficulty, gravity_mode = main_menu()
    
    game = Connect8Game()
    game.set_difficulty(difficulty)
    game.gravity_mode = gravity_mode
    game.connect_n = CONNECT_N
    
    game_running = True
    global clock
    clock = pygame.time.Clock()
    
    while game_running:
        mouse_pos = pygame.mouse.get_pos()
        col = int(mouse_pos[0] // SQUARE_SIZE) if mouse_pos[0] < WIDTH else -1
        row = int((mouse_pos[1] - SQUARE_SIZE) // SQUARE_SIZE) if SQUARE_SIZE <= mouse_pos[1] < (ROWS + 1) * SQUARE_SIZE else -1
        
        # Update the hovered column for column removal or gravity off
        game.hovered_column = col
        game.hovered_row = row
        
        screen.fill(DARK_BLUE)
        
        # Update animations
        game.update_animations()
        
        # Draw the game board
        game.draw_board(screen)
        
        # Draw hover piece if it's player's turn and input isn't locked
        if game.turn == 0 and not game.game_over and not game.lock_player_input:
            if game.gravity_off_active:
                game.draw_hover_piece(screen, col, row)
            else:
                game.draw_hover_piece(screen, col)
        
        # Draw powerups and game info
        game.draw_powerups(screen)
        
        # Draw game status
        game.draw_game_status(screen)
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check if column remover activation/deactivation button was clicked
                if game.turn == 0 and game.player_powerups['column_remover'].active and not game.lock_player_input:
                    if hasattr(game, 'column_remover_button_rect') and game.column_remover_button_rect.collidepoint(mouse_pos):
                        game.column_remover_active = not game.column_remover_active
                        # Deactivate gravity off if it's active
                        if game.column_remover_active and game.gravity_off_active:
                            game.gravity_off_active = False
                        continue  # Skip other checks
                
                # Check if gravity off activation/deactivation button was clicked
                if game.turn == 0 and game.player_powerups['gravity_off'].active and not game.lock_player_input:
                    if hasattr(game, 'gravity_off_button_rect') and game.gravity_off_button_rect.collidepoint(mouse_pos):
                        game.gravity_off_active = not game.gravity_off_active
                        # Deactivate column remover if it's active
                        if game.gravity_off_active and game.column_remover_active:
                            game.column_remover_active = False
                        continue  # Skip other checks
                
                # Handle column removal
                if game.turn == 0 and game.column_remover_active and 0 <= col < COLS and not game.lock_player_input:
                    # Check if clicked on the remove button
                    button_y = (ROWS + 1) * SQUARE_SIZE
                    button_rect = pygame.Rect(col * SQUARE_SIZE, button_y, SQUARE_SIZE, 30)
                    
                    if button_rect.collidepoint(mouse_pos):
                        success = game.use_powerup('column_remover', col)
                        if success:
                            print(f"Successfully removed column {col}")  # Debug info
                        else:
                            print(f"Failed to remove column {col}")  # Debug info
                        game.column_remover_active = False
                        continue  # Skip other checks
                
                # Handle gravity off placement
                if game.turn == 0 and game.gravity_off_active and 0 <= col < COLS and 0 <= row < ROWS and not game.lock_player_input:
                    if game.is_valid_location(col, row) and not game.animated_pieces:
                        # Lock player input during animation and AI turn
                        game.lock_player_input = True
                        # Place piece directly at clicked position
                        success, _ = game.drop_piece(col, game.player_piece, row, True)
                        
                        if success:
                            # Consume the gravity off powerup
                            game.player_powerups['gravity_off'].deactivate()
                            game.gravity_off_active = False
                            
                            # Wait for animation to complete
                            if game.check_win(game.player_piece):
                                game.game_over = True
                                game.winner = 1
                            
                            # Check for powerup after a move
                            got_powerup, powerup_type = game.check_for_powerup()
                            
                            # Set a flag to switch turn after animation completes
                            game.switch_to_ai_after_animation = True
                        continue  # Skip other checks
                
                # Handle player regular moves
                if (game.turn == 0 and not game.game_over and not game.column_remover_active 
                    and not game.gravity_off_active and 0 <= col < COLS and not game.lock_player_input 
                    and not game.animated_pieces):
                    if game.is_valid_location(col):
                        # Lock player input during animation and AI turn
                        game.lock_player_input = True
                        # Normal move
                        success, _ = game.drop_piece(col, game.player_piece)
                        
                        if success:
                            # Wait for animation to complete
                            if game.check_win(game.player_piece):
                                game.game_over = True
                                game.winner = 1
                            
                            # Check for powerup after a move
                            got_powerup, powerup_type = game.check_for_powerup()
                            
                            # Set a flag to switch turn after animation completes
                            game.switch_to_ai_after_animation = True
            
            # Allow players to quit game with Escape key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return  # Return to main menu
        
        # Check if animations are done and we need to switch to AI turn
        if (game.switch_to_ai_after_animation and not game.animated_pieces):
            game.turn = 1  # Switch to AI's turn
            game.switch_to_ai_after_animation = False
        
        # AI's turn
        if game.turn == 1 and not game.game_over and len(game.animated_pieces) == 0:
            if not game.ai_thinking and game.ai_move is None:
                # Start AI thinking in a separate thread
                game.ai_thinking = True
                ai_thread = threading.Thread(target=game.ai_think_thread)
                ai_thread.daemon = True
                ai_thread.start()
            
            elif not game.ai_thinking and game.ai_move is not None:
                # AI has made a decision
                ai_col, ai_row = game.ai_move
                game.ai_move = None
                
                if ai_col is not None:  # If AI didn't use a powerup
                    # Add a short delay before AI moves for better UX
                    pygame.time.wait(300)
                    
                    # For gravity off mode with AI
                    if ai_row is not None and game.ai_powerups['gravity_off'].active:
                        success, _ = game.drop_piece(ai_col, game.ai_piece, ai_row, True)
                        # Consume the gravity off powerup after use
                        game.ai_powerups['gravity_off'].deactivate()
                    else:
                        success, _ = game.drop_piece(ai_col, game.ai_piece)
                    
                    if success:
                        if game.check_win(game.ai_piece):
                            game.game_over = True
                            game.winner = 2
                        
                        # Check for powerup after a move
                        got_powerup, powerup_type = game.check_for_powerup()
                
                # Set a flag to switch turn after AI animation completes
                if not game.animated_pieces:  # If animation completed immediately
                    game.turn = 0  # Switch to player's turn
                    game.lock_player_input = False  # Unlock player input
                else:
                    game.switch_to_player_after_animation = True
        
        # Check if AI animations are done and we need to switch back to player
        if (game.switch_to_player_after_animation and not game.animated_pieces):
            game.turn = 0  # Switch to player's turn
            game.lock_player_input = False  # Unlock player input
            game.switch_to_player_after_animation = False
        
        # Check for draw
        if not game.game_over and len(game.get_valid_locations()) == 0 and len(game.animated_pieces) == 0:
            game.game_over = True
            game.winner = 0  # Draw
        
        # If game is over, show game over screen after a short delay
        if game.game_over and not game.animated_pieces:
            pygame.time.wait(1000)  # Give player time to see the final board
            play_again = show_game_over_screen(game.winner)
            if play_again:
                game.reset_game()  # Reset the game with same settings
            else:
                return  # Return to main menu
        
        pygame.display.update()
        clock.tick(60)

if __name__ == "__main__":
    clock = pygame.time.Clock()  # Initialize the global clock
    while True:
        play_game()
import pygame
import numpy as np
import sys
import math
import random
import time
import threading
import traceback

# Game constants
DARK_BLUE = (0, 51, 102)
LIGHT_BLUE = (51, 153, 255)
BOARD_BLUE = (0, 102, 204)
GOLD = (255, 215, 0)
CRIMSON = (220, 20, 60)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
GREEN = (0, 200, 0)

# Default game settings
DEFAULT_ROW_COUNT = 8
DEFAULT_COLUMN_COUNT = 16
DEFAULT_CONNECT_N = 8
MIN_GRID_SIZE = 8
MAX_GRID_SIZE = 15
SQUARESIZE = 60  # Will be adjusted based on grid size
RADIUS_RATIO = 0.4  # Radius as a proportion of square size
FPS = 60
ANIMATION_SPEED = 15
MAX_AI_THINK_TIME = 3.0

# Initialize pygame
pygame.init()
pygame.display.set_caption('Connect 8 with AI')
clock = pygame.time.Clock()

# Pre-load fonts
title_font = pygame.font.SysFont("Arial", 40, bold=True)
menu_font = pygame.font.SysFont("Arial", 32, bold=True)
info_font = pygame.font.SysFont("Arial", 24)
score_font = pygame.font.SysFont("Arial", 20)
button_font = pygame.font.SysFont("Arial", 24, bold=True)
input_font = pygame.font.SysFont("Arial", 28)

# Game state class
class GameState:
    def __init__(self):
        self.row_count = DEFAULT_ROW_COUNT
        self.column_count = DEFAULT_COLUMN_COUNT
        self.connect_n = DEFAULT_CONNECT_N
        self.squaresize = SQUARESIZE
        self.radius = int(self.squaresize * RADIUS_RATIO)
        self.width = self.column_count * self.squaresize
        self.height = (self.row_count + 1) * self.squaresize + 100
        self.size = (self.width, self.height)
        
        self.board = np.zeros((self.row_count, self.column_count))
        self.game_over = False
        self.in_menu = True
        self.turn = 0  # Always start with player (0=player, 1=AI)
        self.winning_positions = None
        self.winner = 0
        self.ai_thinking = False
        self.ai_move = None
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.fps = 0
        self.difficulty = 1  # 1=Easy, 2=Medium, 3=Hard
        self.difficulty_name = "Easy"
        
        # Custom grid input
        self.custom_grid_active = False
        self.rows_input = ""
        self.cols_input = ""
        self.input_focus = None  # 'rows' or 'cols'
        self.input_error = ""
        
        # Debug
        self.debug_message = ""
        # Power-up tracking
        self.player_powerup_available = False
        self.ai_powerup_available = False
        self.player_powerup_used = False
        self.ai_powerup_used = False
        self.powerup_icon = pygame.image.load("powerup_icon.png")  # Load a power-up icon
        self.powerup_icon = pygame.transform.scale(self.powerup_icon, (50, 50))  # Resize icon
        
    def reset(self):
        self.board = np.zeros((self.row_count, self.column_count))
        self.game_over = False
        self.turn = 0  # Always start with player
        self.winning_positions = None
        self.winner = 0
        self.ai_thinking = False
        self.ai_move = None
        self.debug_message = ""
        
    def update_grid_size(self, rows, cols):
        self.row_count = rows
        self.column_count = cols
        
        # Adjust square size based on grid dimensions to fit screen
        base_width = 800
        base_height = 600
        width_based = base_width // cols
        height_based = (base_height - 100) // (rows + 1)
        self.squaresize = min(width_based, height_based, SQUARESIZE)
        self.radius = int(self.squaresize * RADIUS_RATIO)
        
        self.width = self.column_count * self.squaresize
        self.height = (self.row_count + 1) * self.squaresize + 100
        self.size = (self.width, self.height)
        
        # Reset the board with new dimensions
        self.board = np.zeros((self.row_count, self.column_count))

# Create game state
game_state = GameState()
# Create global screen variable
screen = pygame.display.set_mode(game_state.size, pygame.RESIZABLE)

# Pre-render common text
title_text = title_font.render("CONNECT 8", True, WHITE)
info_text = info_font.render("Connect 8 pieces to win!", True, LIGHT_BLUE)
thinking_texts = [
    info_font.render("AI thinking", True, GOLD),
    info_font.render("AI thinking.", True, GOLD),
    info_font.render("AI thinking..", True, GOLD),
    info_font.render("AI thinking...", True, GOLD)
]

# Button class for menu
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.is_hovered = False
        
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=10)
        
        text_surf = button_font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
        
    def is_clicked(self, pos, click):
        return self.rect.collidepoint(pos) and click

# Input box class for custom grid size
class InputBox:
    def __init__(self, x, y, width, height, text='', label=''):
        self.rect = pygame.Rect(x, y, width, height)
        self.color_inactive = DARK_GRAY
        self.color_active = LIGHT_BLUE
        self.color = self.color_inactive
        self.text = text
        self.label = label
        self.label_surface = info_font.render(label, True, WHITE)
        self.active = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input box
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit() and len(self.text) < 2:  # Only allow 2 digits max
                self.text += event.unicode
            return False
        return False
    
    def update(self):
        # Change the color of the input box
        self.color = self.color_active if self.active else self.color_inactive
    
    def draw(self, surface):
        # Draw the label
        surface.blit(self.label_surface, (self.rect.x, self.rect.y - 25))
        
        # Draw the input box
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=5)
        
        # Render the current text
        txt_surface = input_font.render(self.text, True, WHITE)
        
        # Center the text in the input box
        text_x = self.rect.x + (self.rect.w - txt_surface.get_width()) // 2
        text_y = self.rect.y + (self.rect.h - txt_surface.get_height()) // 2
        
        # Blit the text
        surface.blit(txt_surface, (text_x, text_y))

# Board functions
def create_board(rows, cols):
    return np.zeros((rows, cols))

def drop_piece(board, row, col, piece):
    board[row][col] = piece

def is_valid_location(board, col):
    rows = board.shape[0]
    return 0 <= col < board.shape[1] and board[rows-1][col] == 0

def get_next_open_row(board, col):
    for r in range(board.shape[0]):
        if board[r][col] == 0:
            return r
    return -1

def check_connect_n(board, piece, n):
    """Check for n connected pieces"""
    rows, cols = board.shape
    
    # Check horizontal locations
    for r in range(rows):
        for c in range(cols - n + 1):
            window = [board[r][c+i] for i in range(n)]
            if all(cell == piece for cell in window):
                return [(r, c+i) for i in range(n)]
    
    # Check vertical locations
    for c in range(cols):
        for r in range(rows - n + 1):
            window = [board[r+i][c] for i in range(n)]
            if all(cell == piece for cell in window):
                return [(r+i, c) for i in range(n)]
    
    # Check positively sloped diagonals
    for r in range(rows - n + 1):
        for c in range(cols - n + 1):
            window = [board[r+i][c+i] for i in range(n)]
            if all(cell == piece for cell in window):
                return [(r+i, c+i) for i in range(n)]
    
    # Check negatively sloped diagonals
    for r in range(n - 1, rows):
        for c in range(cols - n + 1):
            window = [board[r-i][c+i] for i in range(n)]
            if all(cell == piece for cell in window):
                return [(r-i, c+i) for i in range(n)]
    
    return False

def winning_move(board, piece):
    """Check if the player with 'piece' has won"""
    return check_connect_n(board, piece, game_state.connect_n)

# Optimized evaluation function for Connect N
def evaluate_window(window, piece, n):
    """Evaluate a window of n pieces"""
    opp_piece = 1 if piece == 2 else 2
    
    # Count pieces
    piece_count = window.count(piece)
    empty_count = window.count(0)
    opp_count = window.count(opp_piece)
    
    # Scoring logic - adjusted for Connect N
    if piece_count == n:
        return 1000000  # Winning move
    
    # Progressive scoring based on how many pieces in a row
    if empty_count > 0:
        if piece_count >= n - 1:
            return 50000  # Almost winning (n-1 in a row)
        elif piece_count >= n - 2:
            return 10000  # n-2 in a row
        elif piece_count >= n - 3:
            return 1000   # n-3 in a row
        elif piece_count >= n - 4:
            return 100    # n-4 in a row
        elif piece_count >= 3:
            return 10     # 3 in a row
        elif piece_count >= 2:
            return 2      # 2 in a row
    
    # Defensive scoring
    if opp_count >= n - 1 and empty_count == 1:
        return -50000  # Block opponent's almost win
    elif opp_count >= n - 2 and empty_count == 2:
        return -10000  # Block opponent's n-2 in a row
    
    return 0

def evaluate_position(board, piece):
    """Evaluate the entire board position"""
    rows, cols = board.shape
    n = game_state.connect_n
    score = 0
    opp_piece = 1 if piece == 2 else 2
    
    # Center column preference
    center_col = cols // 2
    center_array = [int(board[r][center_col]) for r in range(rows)]
    center_count = center_array.count(piece)
    score += center_count * 3
    
    # Evaluate all possible windows
    # Horizontal windows
    for r in range(rows):
        for c in range(cols - n + 1):
            window = [int(board[r][c+i]) for i in range(n)]
            score += evaluate_window(window, piece, n)
    
    # Vertical windows
    for c in range(cols):
        for r in range(rows - n + 1):
            window = [int(board[r+i][c]) for i in range(n)]
            score += evaluate_window(window, piece, n)
    
    # Positive diagonal windows
    for r in range(rows - n + 1):
        for c in range(cols - n + 1):
            window = [int(board[r+i][c+i]) for i in range(n)]
            score += evaluate_window(window, piece, n)
    
    # Negative diagonal windows
    for r in range(n - 1, rows):
        for c in range(cols - n + 1):
            window = [int(board[r-i][c+i]) for i in range(n)]
            score += evaluate_window(window, piece, n)
    
    return score

def is_terminal_node(board):
    return winning_move(board, 1) or winning_move(board, 2) or len(get_valid_locations(board)) == 0

def get_valid_locations(board):
    valid_locations = []
    cols = board.shape[1]
    # Check center columns first for better alpha-beta pruning
    center = cols // 2
    for offset in range(cols):
        if offset % 2 == 0:
            col = center + offset // 2
        else:
            col = center - (offset + 1) // 2
            
        if 0 <= col < cols and is_valid_location(board, col):
            valid_locations.append(col)
    return valid_locations

# AI move functions based on difficulty
def get_easy_move(board):
    """Easy difficulty: Random valid move"""
    valid_locations = get_valid_locations(board)
    if valid_locations:
        return random.choice(valid_locations)
    return None

def get_medium_move(board, piece):
    """Medium difficulty: Minimax with limited depth (3)"""
    try:
        start_time = time.time()
        col, _ = minimax(board, 3, -math.inf, math.inf, True, start_time, piece)
        return col
    except TimeoutError:
        return get_easy_move(board)

def get_hard_move(board, piece):
    """Hard difficulty: Full Minimax with Alpha-Beta Pruning"""
    try:
        return find_best_move(board, 5, piece)  # Depth 5 for hard
    except TimeoutError:
        return get_medium_move(board, piece)

def find_best_move(board, depth, piece):
    """Wrapper function that runs minimax with a time limit"""
    valid_locations = get_valid_locations(board)
    if not valid_locations:
        return None
    
    # Start with a random valid move as fallback
    best_col = random.choice(valid_locations)
    
    # Use iterative deepening to ensure we always have a move
    for current_depth in range(1, depth + 1):
        try:
            start_time = time.time()
            col, score = minimax(board, current_depth, -math.inf, math.inf, True, start_time, piece)
            if col is not None:
                best_col = col
            
            # If we're running out of time, stop deepening
            if time.time() - start_time > MAX_AI_THINK_TIME * 0.8:
                break
                
        except TimeoutError:
            # If we timeout, use the best move from the previous depth
            break
    
    return best_col

def minimax(board, depth, alpha, beta, maximizing_player, start_time, piece):
    # Check if we're out of time
    if time.time() - start_time > MAX_AI_THINK_TIME:
        raise TimeoutError("AI thinking took too long")
    
    valid_locations = get_valid_locations(board)
    is_terminal = is_terminal_node(board)
    
    if depth == 0 or is_terminal:
        if is_terminal:
            if winning_move(board, piece):  # AI wins
                return (None, 1000000)
            elif winning_move(board, 3 - piece):  # Player wins (3-piece gives opponent)
                return (None, -1000000)
            else:  # Game is over, no more valid moves
                return (None, 0)
        else:  # Depth is zero
            return (None, evaluate_position(board, piece))
    
    if maximizing_player:
        value = -math.inf
        column = random.choice(valid_locations) if valid_locations else None
        
        for col in valid_locations:
            row = get_next_open_row(board, col)
            b_copy = board.copy()
            drop_piece(b_copy, row, col, piece)
            new_score = minimax(b_copy, depth-1, alpha, beta, False, start_time, piece)[1]
            
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
            row = get_next_open_row(board, col)
            b_copy = board.copy()
            drop_piece(b_copy, row, col, 3 - piece)  # Opponent's piece
            new_score = minimax(b_copy, depth-1, alpha, beta, True, start_time, piece)[1]
            
            if new_score < value:
                value = new_score
                column = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return column, value

# Rendering functions
def draw_board(board, winning_positions=None):
    # Draw the background
    pygame.draw.rect(screen, DARK_BLUE, (0, 0, game_state.width, game_state.height - 100))
    pygame.draw.rect(screen, DARK_GRAY, (0, game_state.height - 100, game_state.width, 100))
    
    # Draw game title and info
    screen.blit(title_text, (game_state.width//2 - title_text.get_width()//2, game_state.height - 90))
    
    # Draw connect info
    connect_text = info_font.render(f"Connect {game_state.connect_n} to win!", True, LIGHT_BLUE)
    screen.blit(connect_text, (game_state.width//2 - connect_text.get_width()//2, game_state.height - 50))
    
    # Draw FPS counter
    fps_text = score_font.render(f"FPS: {game_state.fps}", True, WHITE)
    screen.blit(fps_text, (10, game_state.height - 30))
    
    # Draw difficulty level
    diff_text = score_font.render(f"AI Level: {game_state.difficulty_name}", True, WHITE)
    screen.blit(diff_text, (game_state.width - 150, game_state.height - 30))
    
    # Draw whose turn it is
    turn_text = score_font.render("YOUR TURN" if game_state.turn == 0 else "AI'S TURN", True, 
                                 CRIMSON if game_state.turn == 0 else GOLD)
    screen.blit(turn_text, (game_state.width//2 - turn_text.get_width()//2, 30))
    
    # Draw debug message if any
    if game_state.debug_message:
        debug_text = score_font.render(game_state.debug_message, True, WHITE)
        screen.blit(debug_text, (10, 10))
    
    # Draw the board frame
    pygame.draw.rect(screen, DARK_GRAY, (0, game_state.squaresize, game_state.width, game_state.row_count*game_state.squaresize))
    
    # Draw the board slots and pieces
    for c in range(game_state.column_count):
        for r in range(game_state.row_count):
            # Position calculation
            x = int(c*game_state.squaresize+game_state.squaresize/2)
            y = int((r+1)*game_state.squaresize+game_state.squaresize/2)
            y_inv = game_state.height - 100 - (game_state.row_count-r)*game_state.squaresize + game_state.squaresize//2
            
            # Draw slot
            pygame.draw.circle(screen, BOARD_BLUE, (x, y), game_state.radius)
            
            # Draw pieces
            if board[r][c] == 1:  # Player piece
                pygame.draw.circle(screen, CRIMSON, (x, y_inv), game_state.radius)
                # Simple highlight for 3D effect
                pygame.draw.circle(screen, (255, 100, 100), (x - 3, y_inv - 3), game_state.radius//4)
                
            elif board[r][c] == 2:  # AI piece
                pygame.draw.circle(screen, GOLD, (x, y_inv), game_state.radius)
                # Simple highlight for 3D effect
                pygame.draw.circle(screen, (255, 255, 150), (x - 3, y_inv - 3), game_state.radius//4)
    
    # Highlight winning pieces if any
    if winning_positions:
        for r, c in winning_positions:
            x = int(c*game_state.squaresize+game_state.squaresize/2)
            y_inv = game_state.height - 100 - (game_state.row_count-r)*game_state.squaresize + game_state.squaresize//2
            
            # Simple pulsating effect based on time
            pulse = int(3 * math.sin(time.time() * 8)) + 3
            pygame.draw.circle(screen, WHITE, (x, y_inv), game_state.radius + pulse, 2)
    
    # Draw the column indicators
    # for c in range(game_state.column_count):
    #     if c % 2 == 0:  # Only show every other column number to avoid crowding
    #         text = score_font.render(str(c+1), True, GRAY)
    #         screen.blit(text, (c*game_state.squaresize + game_state.squaresize//2, game_state.squaresize//2))

def draw_hover_piece(col, turn):
    """Draw the piece that follows the mouse when hovering"""
    # Clear the top area
    pygame.draw.rect(screen, DARK_BLUE, (0, 0, game_state.width, game_state.squaresize))
    
    # Draw turn indicator
    turn_text = score_font.render("YOUR TURN" if game_state.turn == 0 else "AI'S TURN", True, 
                                 CRIMSON if game_state.turn == 0 else GOLD)
    screen.blit(turn_text, (game_state.width//2 - turn_text.get_width()//2, 30))
    
    # Draw debug message if any
    if game_state.debug_message:
        debug_text = score_font.render(game_state.debug_message, True, WHITE)
        screen.blit(debug_text, (10, 10))
    
    # Draw the hovering piece
    if 0 <= col < game_state.column_count:
        color = CRIMSON if turn == 0 else GOLD
        pygame.draw.circle(screen, color, 
                          (col*game_state.squaresize + game_state.squaresize//2, game_state.squaresize//2), 
                          game_state.radius)

def animate_drop(board, row, col, piece, frames=8):
    """Animate piece dropping with physics-based acceleration"""
    # Calculate positions
    final_y = game_state.height - 100 - (game_state.row_count-row)*game_state.squaresize + game_state.squaresize//2
    start_y = game_state.squaresize//2
    x = int(col*game_state.squaresize+game_state.squaresize/2)
    
    # Pre-calculate all frame positions with acceleration
    positions = []
    for i in range(frames + 1):
        t = i / frames  # Normalized time from 0 to 1
        # Quadratic ease-in function for natural acceleration
        ease_t = t * t  
        y = int(start_y + (final_y - start_y) * ease_t)
        positions.append(y)
    
    # Draw each frame
    color = CRIMSON if piece == 1 else GOLD
    highlight_color = (255, 100, 100) if piece == 1 else (255, 255, 150)
    
    for y in positions:
        # Redraw the board
        draw_board(board, game_state.winning_positions)
        
        # Draw the falling piece
        pygame.draw.circle(screen, color, (x, y), game_state.radius)
        pygame.draw.circle(screen, highlight_color, (x - 3, y - 3), game_state.radius//4)
        
        pygame.display.update()
        clock.tick(FPS)  # Control animation speed with FPS limiter
    
    # Update the actual board
    board[row][col] = piece

def draw_game_over(winner):
    """Draw game over screen with winner announcement"""
    # Semi-transparent overlay
    overlay = pygame.Surface((game_state.width, game_state.height))
    overlay.set_alpha(180)
    overlay.fill(BLACK)
    screen.blit(overlay, (0, 0))
    
    # Winner text
    if winner == 1:
        text = title_font.render("YOU WIN!", True, CRIMSON)
    elif winner == 2:
        text = title_font.render("AI WINS!", True, GOLD)
    else:
        text = title_font.render("IT'S A TIE!", True, WHITE)
    
    screen.blit(text, (game_state.width//2 - text.get_width()//2, game_state.height//2 - 80))
    
    # Instructions
    restart_text = info_font.render("Press SPACE to play again", True, WHITE)
    screen.blit(restart_text, (game_state.width//2 - restart_text.get_width()//2, game_state.height//2 - 20))
    
    menu_text = info_font.render("Press M to return to menu", True, WHITE)
    screen.blit(menu_text, (game_state.width//2 - menu_text.get_width()//2, game_state.height//2 + 20))
    
    quit_text = info_font.render("Press ESC to quit", True, WHITE)
    screen.blit(quit_text, (game_state.width//2 - quit_text.get_width()//2, game_state.height//2 + 60))

def draw_menu():
    """Draw the main menu screen"""
    # Fill background
    screen.fill(DARK_BLUE)
    
    # Title
    title = title_font.render("CONNECT 8 WITH AI", True, WHITE)
    screen.blit(title, (game_state.width//2 - title.get_width()//2, 50))
    
    # Subtitle
    subtitle = info_font.render("A Strategic Board Game with Adaptive AI", True, LIGHT_BLUE)
    screen.blit(subtitle, (game_state.width//2 - subtitle.get_width()//2, 100))
    
    # Create buttons
    button_width = 200
    button_height = 50
    button_x = game_state.width//2 - button_width//2
    
    # Difficulty buttons
    diff_label = menu_font.render("Select Difficulty:", True, WHITE)
    screen.blit(diff_label, (button_x, 160))
    
    easy_button = Button(button_x, 200, button_width, button_height, "Easy", DARK_GRAY, CRIMSON)
    medium_button = Button(button_x, 260, button_width, button_height, "Medium", DARK_GRAY, CRIMSON)
    hard_button = Button(button_x, 320, button_width, button_height, "Hard", DARK_GRAY, CRIMSON)
    
    # Custom grid size button and input boxes
    grid_label = menu_font.render("Grid Size:", True, WHITE)
    screen.blit(grid_label, (button_x, 390))
    
    custom_grid_button = Button(button_x, 430, button_width, button_height, "Custom Grid", DARK_GRAY, GOLD)
    
    # Draw input boxes if custom grid is active
    rows_input = None
    cols_input = None
    if game_state.custom_grid_active:
        rows_input = InputBox(button_x - 120, 500, 80, 40, game_state.rows_input, "Rows")
        cols_input = InputBox(button_x + 40, 500, 80, 40, game_state.cols_input, "Columns")
        
        rows_input.active = game_state.input_focus == 'rows'
        cols_input.active = game_state.input_focus == 'cols'
        
        rows_input.update()
        cols_input.update()
        
        rows_input.draw(screen)
        cols_input.draw(screen)
        
        # Draw range info
        range_text = info_font.render(f"Range: {MIN_GRID_SIZE}-{MAX_GRID_SIZE}", True, LIGHT_BLUE)
        screen.blit(range_text, (button_x - range_text.get_width()//2 + 100, 550))
        
        # Draw error message if any
        if game_state.input_error:
            error_text = info_font.render(game_state.input_error, True, CRIMSON)
            screen.blit(error_text, (button_x - error_text.get_width()//2 + 100, 580))
    
    # Start game button
    start_button = Button(button_x, 620 if game_state.custom_grid_active else 500, 
                         button_width, button_height, "Start Game", GREEN, (0, 255, 0))
    
    # Highlight current selections
    if game_state.difficulty == 1:
        easy_button.color = (100, 0, 0)
    elif game_state.difficulty == 2:
        medium_button.color = (100, 0, 0)
    else:
        hard_button.color = (100, 0, 0)
    
    # Draw all buttons
    easy_button.draw(screen)
    medium_button.draw(screen)
    hard_button.draw(screen)
    custom_grid_button.draw(screen)
    start_button.draw(screen)
    
    # Return all buttons and input boxes for interaction
    buttons = {
        'easy': easy_button,
        'medium': medium_button,
        'hard': hard_button,
        'custom_grid': custom_grid_button,
        'start': start_button
    }
    
    return buttons, rows_input, cols_input

def ai_think_thread(board, difficulty):
    """Separate thread for AI thinking to prevent UI freezing"""
    try:
        # Choose AI move based on difficulty
        if difficulty == 1:  # Easy
            col = get_easy_move(board)
        elif difficulty == 2:  # Medium
            col = get_medium_move(board, 2)
        else:  # Hard
            col = get_hard_move(board, 2)
            
        game_state.ai_move = col
    except Exception as e:
        print(f"AI thinking error: {e}")
        # Fallback to random move if there's an error
        valid_locations = get_valid_locations(board)
        if valid_locations:
            game_state.ai_move = random.choice(valid_locations)
        else:
            game_state.ai_move = -1  # No valid moves
    finally:
        game_state.ai_thinking = False

def update_fps():
    """Calculate and update FPS"""
    current_time = time.time()
    game_state.frame_count += 1
    
    # Update FPS every second
    if current_time - game_state.last_frame_time >= 1.0:
        game_state.fps = game_state.frame_count
        game_state.frame_count = 0
        game_state.last_frame_time = current_time

def main():
    # Initialize game
    game_state.reset()
    
    # Main game loop
    running = True
    thinking_animation_frame = 0
    last_thinking_update = time.time()
    
    while running:
        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            # Handle window resize
            if event.type == pygame.VIDEORESIZE:
                # Recalculate screen size based on current grid
                game_state.update_grid_size(game_state.row_count, game_state.column_count)
                global screen
                screen = pygame.display.set_mode(game_state.size, pygame.RESIZABLE)
            
            # Menu handling
            if game_state.in_menu:
                buttons, rows_input, cols_input = draw_menu()
                
                if event.type == pygame.MOUSEMOTION:
                    # Update button hover states
                    for button in buttons.values():
                        button.check_hover(mouse_pos)
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Handle difficulty selection
                    if buttons['easy'].is_clicked(mouse_pos, True):
                        game_state.difficulty = 1
                        game_state.difficulty_name = "Easy"
                    elif buttons['medium'].is_clicked(mouse_pos, True):
                        game_state.difficulty = 2
                        game_state.difficulty_name = "Medium"
                    elif buttons['hard'].is_clicked(mouse_pos, True):
                        game_state.difficulty = 3
                        game_state.difficulty_name = "Hard"
                    
                    # Handle custom grid button
                    if buttons['custom_grid'].is_clicked(mouse_pos, True):
                        game_state.custom_grid_active = not game_state.custom_grid_active
                        game_state.input_error = ""
                    
                    # Handle input box clicks
                    if game_state.custom_grid_active and rows_input and cols_input:
                        if rows_input.handle_event(event):
                            game_state.input_focus = 'rows'
                            game_state.rows_input = rows_input.text
                        elif cols_input.handle_event(event):
                            game_state.input_focus = 'cols'
                            game_state.cols_input = cols_input.text
                        else:
                            game_state.input_focus = None
                    
                    # Start game
                    if buttons['start'].is_clicked(mouse_pos, True):
                        if game_state.custom_grid_active:
                            # Validate custom grid inputs
                            try:
                                rows = int(game_state.rows_input) if game_state.rows_input else 0
                                cols = int(game_state.cols_input) if game_state.cols_input else 0
                                
                                if MIN_GRID_SIZE <= rows <= MAX_GRID_SIZE and MIN_GRID_SIZE <= cols <= MAX_GRID_SIZE:
                                    game_state.update_grid_size(rows, cols)
                                    screen = pygame.display.set_mode(game_state.size, pygame.RESIZABLE)
                                    game_state.in_menu = False
                                    game_state.reset()
                                else:
                                    game_state.input_error = f"Grid size must be between {MIN_GRID_SIZE} and {MAX_GRID_SIZE}"
                            except ValueError:
                                game_state.input_error = "Please enter valid numbers"
                        else:
                            game_state.in_menu = False
                            game_state.reset()
                
                # Handle keyboard input for custom grid
                if event.type == pygame.KEYDOWN and game_state.custom_grid_active:
                    if game_state.input_focus == 'rows' and rows_input:
                        if rows_input.handle_event(event):
                            game_state.rows_input = rows_input.text
                    elif game_state.input_focus == 'cols' and cols_input:
                        if cols_input.handle_event(event):
                            game_state.cols_input = cols_input.text
            
            # Game handling
            elif not game_state.game_over:
                if event.type == pygame.MOUSEMOTION and not game_state.ai_thinking:
                    # Show hover piece in normal mode (only during player's turn)
                    if game_state.turn == 0:
                        posx = event.pos[0]
                        col = int(math.floor(posx/game_state.squaresize))
                        draw_hover_piece(col, game_state.turn)
                
                if event.type == pygame.MOUSEBUTTONDOWN and game_state.turn == 0:  # Only process clicks during player's turn
                    # Handle normal player turn
                    if not game_state.ai_thinking:
                        posx = event.pos[0]
                        col = int(math.floor(posx/game_state.squaresize))
                        
                        if 0 <= col < game_state.column_count and is_valid_location(game_state.board, col):
                            row = get_next_open_row(game_state.board, col)
                            if row >= 0:  # Make sure we have a valid row
                                animate_drop(game_state.board, row, col, 1)
                                
                                # Check for connect 8 (win)
                                game_state.winning_positions = winning_move(game_state.board, 1)
                                if game_state.winning_positions:
                                    game_state.winner = 1
                                    game_state.game_over = True
                                    continue
                                
                                # Check for game over (board full)
                                if len(get_valid_locations(game_state.board)) == 0:
                                    game_state.game_over = True
                                else:
                                    # Important: Switch to AI's turn
                                    game_state.turn = 1
                                    game_state.debug_message = "Switched to AI turn"
            
            # Game over handling
            elif game_state.game_over and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Restart game with same settings
                    game_state.reset()
                elif event.key == pygame.K_m:
                    # Return to menu
                    game_state.in_menu = True
                    game_state.game_over = False
                elif event.key == pygame.K_ESCAPE:
                    running = False
        
        # Menu rendering
        if game_state.in_menu:
            draw_menu()
        
        # Game rendering and logic
        elif not game_state.game_over:
            # AI's turn
            if game_state.turn == 1:
                if not game_state.ai_thinking and game_state.ai_move is None:
                    # Start AI thinking in a separate thread
                    game_state.ai_thinking = True
                    ai_thread = threading.Thread(
                        target=ai_think_thread, 
                        args=(game_state.board.copy(), game_state.difficulty)
                    )
                    ai_thread.daemon = True
                    ai_thread.start()
                
                elif game_state.ai_thinking:
                    # Show thinking animation while AI is calculating
                    current_time = time.time()
                    if current_time - last_thinking_update > 0.2:  # Update animation every 200ms
                        thinking_animation_frame = (thinking_animation_frame + 1) % 4
                        last_thinking_update = current_time
                    
                    # Draw the board and thinking indicator
                    draw_board(game_state.board, game_state.winning_positions)
                    screen.blit(thinking_texts[thinking_animation_frame], (game_state.width//2 - 80, game_state.squaresize//2 - 15))
                    
                elif game_state.ai_move is not None:
                    # AI has made a decision
                    col = game_state.ai_move
                    game_state.ai_move = None
                    
                    if col is not None and 0 <= col < game_state.column_count and is_valid_location(game_state.board, col):
                        row = get_next_open_row(game_state.board, col)
                        if row >= 0:  # Make sure we have a valid row
                            animate_drop(game_state.board, row, col, 2)
                            
                            # Check for connect 8 (win)
                            game_state.winning_positions = winning_move(game_state.board, 2)
                            if game_state.winning_positions:
                                game_state.winner = 2
                                game_state.game_over = True
                            else:
                                # Check for game over (board full)
                                if len(get_valid_locations(game_state.board)) == 0:
                                    game_state.game_over = True
                                else:
                                    # Important: Switch back to player's turn
                                    game_state.turn = 0
                                    game_state.debug_message = "Switched to player turn"
            
            # Draw the current state
            if not game_state.ai_thinking or game_state.game_over:
                draw_board(game_state.board, game_state.winning_positions)
        
        # Draw game over screen if game is over
        if game_state.game_over:
            draw_game_over(game_state.winner)
        
        # Update display and maintain frame rate
        pygame.display.update()
        update_fps()
        clock.tick(FPS)
    
    # Clean up
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())  # Print full traceback for debugging
        pygame.quit()
        sys.exit(1)


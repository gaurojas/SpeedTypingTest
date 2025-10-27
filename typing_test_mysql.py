import time
import random
import os
import sys
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# For real-time character input
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Unix/Linux/Mac
    import tty
    import termios

# Color codes for terminal
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

class KeyboardInput:
    """Handle real-time keyboard input across platforms"""
    
    @staticmethod
    def get_char():
        """Get a single character from keyboard without blocking"""
        if os.name == 'nt':  # Windows
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char == b'\xe0':  # Special key
                    msvcrt.getch()
                    return None
                elif char == b'\r':
                    return '\n'
                elif char == b'\x08':
                    return '\b'
                elif char == b'\x1b':
                    return '\x1b'
                try:
                    return char.decode('utf-8')
                except:
                    return None
            return None
        else:  # Unix/Linux/Mac
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    char = sys.stdin.read(1)
                    if char == '\x7f':
                        return '\b'
                    elif char == '\x1b':
                        # Handle escape sequences
                        next_chars = sys.stdin.read(2)
                        return None  # Ignore arrow keys
                    return char
                return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class Database:
    def __init__(self):
        self.connection = None
        
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='gaurojas#702',
                database='typing_test_db'
            )
            if self.connection.is_connected():
                return True
        except Error as e:
            print(f"{Colors.RED}Database connection failed: {e}{Colors.RESET}")
            return False
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT,
                    wpm DECIMAL(6,2),
                    accuracy DECIMAL(5,2),
                    raw_wpm DECIMAL(6,2),
                    errors INT,
                    difficulty ENUM('easy', 'medium', 'hard', 'extreme'),
                    time_taken INT,
                    test_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    INDEX idx_wpm (wpm DESC),
                    INDEX idx_difficulty (difficulty),
                    INDEX idx_date (test_date DESC)
                )
            """)
            
            self.connection.commit()
            return True
        except Error as e:
            print(f"{Colors.RED}Error creating tables: {e}{Colors.RESET}")
            return False
    
    def get_or_create_user(self, username):
        """Get user ID or create new user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if result:
                return result[0]
            else:
                cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
                self.connection.commit()
                return cursor.lastrowid
        except Error as e:
            print(f"{Colors.RED}Error with user: {e}{Colors.RESET}")
            return None
    
    def save_result(self, user_id, wpm, accuracy, raw_wpm, errors, difficulty, time_taken):
        """Save test result to database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO test_results (user_id, wpm, accuracy, raw_wpm, errors, difficulty, time_taken)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, wpm, accuracy, raw_wpm, errors, difficulty, time_taken))
            self.connection.commit()
            return True
        except Error as e:
            print(f"{Colors.RED}Error saving result: {e}{Colors.RESET}")
            return False
    
    def get_leaderboard(self, difficulty=None, limit=10):
        """Get leaderboard data"""
        try:
            cursor = self.connection.cursor()
            if difficulty:
                query = """
                    SELECT u.username, t.wpm, t.accuracy, t.test_date, t.difficulty
                    FROM test_results t
                    JOIN users u ON t.user_id = u.id
                    WHERE t.difficulty = %s
                    ORDER BY t.wpm DESC, t.accuracy DESC
                    LIMIT %s
                """
                cursor.execute(query, (difficulty, limit))
            else:
                query = """
                    SELECT u.username, t.wpm, t.accuracy, t.test_date, t.difficulty
                    FROM test_results t
                    JOIN users u ON t.user_id = u.id
                    ORDER BY t.wpm DESC, t.accuracy DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            return cursor.fetchall()
        except Error as e:
            print(f"{Colors.RED}Error fetching leaderboard: {e}{Colors.RESET}")
            return []
    
    def get_user_stats(self, user_id):
        """Get user statistics"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tests,
                    AVG(wpm) as avg_wpm,
                    MAX(wpm) as best_wpm,
                    AVG(accuracy) as avg_accuracy,
                    MAX(accuracy) as best_accuracy
                FROM test_results
                WHERE user_id = %s
            """, (user_id,))
            
            return cursor.fetchone()
        except Error as e:
            print(f"{Colors.RED}Error fetching user stats: {e}{Colors.RESET}")
            return None
    
    def get_user_rank(self, user_id, difficulty=None):
        """Get user's rank on leaderboard"""
        try:
            cursor = self.connection.cursor()
            if difficulty:
                query = """
                    SELECT COUNT(*) + 1 AS `user_rank`
                    FROM test_results t1
                    WHERE t1.difficulty = %s
                    AND (t1.wpm > (
                        SELECT MAX(wpm) FROM test_results WHERE user_id = %s AND difficulty = %s
                    ) OR (t1.wpm = (
                        SELECT MAX(wpm) FROM test_results WHERE user_id = %s AND difficulty = %s
                    ) AND t1.accuracy > (
                        SELECT MAX(accuracy) FROM test_results WHERE user_id = %s AND difficulty = %s
                    )))
                """
                cursor.execute(query, (difficulty, user_id, difficulty, user_id, difficulty, user_id, difficulty))
            else:
                query = """
                    SELECT COUNT(*) + 1 AS `user_rank`
                    FROM test_results t1
                    WHERE (t1.wpm > (
                        SELECT MAX(wpm) FROM test_results WHERE user_id = %s
                    ) OR (t1.wpm = (
                        SELECT MAX(wpm) FROM test_results WHERE user_id = %s
                    ) AND t1.accuracy > (
                        SELECT MAX(accuracy) FROM test_results WHERE user_id = %s
                    )))
                """
                cursor.execute(query, (user_id, user_id, user_id))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except Error as e:
            print(f"{Colors.RED}Error fetching rank: {e}{Colors.RESET}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()

class TypingTest:
    def __init__(self):
        self.db = Database()
        self.current_user_id = None
        self.username = None
        self.keyboard = KeyboardInput()
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def move_cursor(self, x, y):
        """Move cursor to position (x, y)"""
        print(f"\033[{y};{x}H", end='', flush=True)
    
    def hide_cursor(self):
        """Hide terminal cursor"""
        print('\033[?25l', end='', flush=True)
    
    def show_cursor(self):
        """Show terminal cursor"""
        print('\033[?25h', end='', flush=True)
    
    def load_text(self, difficulty):
        """Load random paragraph from text file"""
        filename = f"text_{difficulty}.txt"
        
        if not os.path.exists(filename):
            print(f"{Colors.RED}Error: {filename} not found!{Colors.RESET}")
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            paragraphs = [p.strip() for p in content.split('###PARA') if p.strip()]
            
            if not paragraphs:
                print(f"{Colors.RED}Error: No paragraphs found in {filename}!{Colors.RESET}")
                return None
            
            return random.choice(paragraphs)
        except Exception as e:
            print(f"{Colors.RED}Error loading text: {e}{Colors.RESET}")
            return None
    
    def calculate_wpm(self, chars_typed, time_taken, errors):
        """Calculate WPM (Words Per Minute)"""
        if time_taken <= 0:
            return 0, 0
        minutes = time_taken / 60
        gross_wpm = (chars_typed / 5) / minutes
        net_wpm = max(0, ((chars_typed / 5) - errors) / minutes)
        return round(gross_wpm, 2), round(net_wpm, 2)
    
    def wrap_text(self, text, width=80):
        """Wrap text to fit in terminal width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) <= width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def display_typing_interface(self, text, typed_text, errors, start_time, current_wpm):
        """Display the typing interface with colored text"""
        # Clear the screen and render content. Cursor visibility is managed
        # once when the live test starts/stops to avoid flicker from
        # repeatedly hiding/showing the cursor on every frame.
        self.clear_screen()
        
        # Header
        print(f"\n{Colors.CYAN}{Colors.BOLD}╔{'═' * 78}╗{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}║{' ' * 28}TYPING TEST{' ' * 39}║{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}╚{'═' * 78}╝{Colors.RESET}\n")
        
        # Stats bar
        elapsed = time.time() - start_time if start_time else 0
        correct_chars = len(typed_text) - errors
        accuracy = (correct_chars / max(len(typed_text), 1) * 100) if typed_text else 100
        
        stats = f"  WPM: {Colors.GREEN}{current_wpm}{Colors.RESET}  |  "
        stats += f"Accuracy: {Colors.GREEN if accuracy >= 95 else Colors.YELLOW if accuracy >= 85 else Colors.RED}{accuracy:.1f}%{Colors.RESET}  |  "
        stats += f"Errors: {Colors.RED}{errors}{Colors.RESET}  |  "
        stats += f"Time: {Colors.CYAN}{elapsed:.1f}s{Colors.RESET}"
        print(stats)
        print(f"{Colors.CYAN}{'─' * 80}{Colors.RESET}\n")
        
        # Display text with colors
        current_pos = len(typed_text)
        wrapped_text = self.wrap_text(text, 78)
        
        output = ""
        char_idx = 0
        for char in text:
            if char_idx < current_pos:
                # Already typed
                if char_idx < len(typed_text):
                    if typed_text[char_idx] == char:
                        # Correct - green
                        output += f"{Colors.GREEN}{char}{Colors.RESET}"
                    else:
                        # Wrong - red background with original character
                        if typed_text[char_idx] == ' ':
                            output += f"{Colors.RED}{Colors.UNDERLINE}_{Colors.RESET}"
                        else:
                            output += f"{Colors.RED}{Colors.BOLD}{char}{Colors.RESET}"
                else:
                    output += f"{Colors.GRAY}{char}{Colors.RESET}"
            elif char_idx == current_pos:
                # Current position - yellow background
                output += f"{Colors.YELLOW}{Colors.UNDERLINE}{char}{Colors.RESET}"
            else:
                # Not yet typed - gray
                output += f"{Colors.GRAY}{char}{Colors.RESET}"
            
            char_idx += 1
        
        print(output)
        print(f"\n{Colors.CYAN}{'─' * 80}{Colors.RESET}")
        print(f"{Colors.DIM}ESC to quit | Backspace to correct | Type to continue{Colors.RESET}\n")
        
    # Do NOT show the cursor here; the cursor is restored when the
    # live test finishes to avoid per-frame cursor flicker.
    
    def run_test_live(self, difficulty):
        """Run the typing test with real-time character-by-character feedback"""
        text = self.load_text(difficulty)
        if not text:
            return
        
        # Show preview
        print(f"\n{Colors.GREEN}{Colors.BOLD}Get ready to type!{Colors.RESET}")
        print(f"\n{Colors.CYAN}Difficulty: {difficulty.upper()}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}The text will appear in gray. Type each character exactly as shown.{Colors.RESET}")
        print(f"{Colors.YELLOW}• Correct characters will turn {Colors.GREEN}GREEN{Colors.RESET}")
        print(f"{Colors.YELLOW}• Wrong characters will turn {Colors.RED}RED{Colors.RESET}")
        print(f"{Colors.YELLOW}• The current character to type is {Colors.YELLOW}{Colors.UNDERLINE}HIGHLIGHTED{Colors.RESET}")
        print(f"\n{Colors.BOLD}Text preview:{Colors.RESET}")
        print(f"\n{Colors.GRAY}{text[:150]}...{Colors.RESET}")
        input(f"\n{Colors.GREEN}Press ENTER when ready...{Colors.RESET}")
        
        typed_text = ""
        errors = 0
        start_time = None
        current_wpm = 0
        last_update = 0
        # Hide cursor once before entering the live update loop to avoid
        # repeated hide/show (which causes visible flicker in some terminals).
        self.hide_cursor()
        
        try:
            while len(typed_text) < len(text):
                # Display current state
                self.display_typing_interface(text, typed_text, errors, start_time, current_wpm)
                
                # Wait for character
                char = None
                while char is None:
                    char = self.keyboard.get_char()
                    time.sleep(0.01)
                    
                    # Update WPM periodically
                    # Reduce redraw frequency to avoid excessive screen
                    # clears which can produce flicker.
                    if start_time and time.time() - last_update > 0.5:
                        elapsed = time.time() - start_time
                        _, current_wpm = self.calculate_wpm(len(typed_text), elapsed, errors)
                        last_update = time.time()
                        self.display_typing_interface(text, typed_text, errors, start_time, current_wpm)
                
                # Start timer on first character
                if start_time is None and char not in ['\b', '\x1b']:
                    start_time = time.time()
                    last_update = start_time
                
                # Handle ESC
                if char == '\x1b':
                    self.show_cursor()
                    print(f"\n\n{Colors.RED}Test cancelled!{Colors.RESET}")
                    return
                
                # Handle backspace
                elif char == '\b':
                    if len(typed_text) > 0:
                        # Check if we're removing an error
                        if typed_text[-1] != text[len(typed_text) - 1]:
                            errors = max(0, errors - 1)
                        typed_text = typed_text[:-1]
                
                # Handle regular character (including spaces and newlines)
                elif char:
                    typed_text += char
                    
                    # Check if character is correct
                    if len(typed_text) <= len(text):
                        expected_char = text[len(typed_text) - 1]
                        if char != expected_char:
                            errors += 1
            
            # Test completed
            self.display_typing_interface(text, typed_text, errors, start_time, current_wpm)
            time.sleep(1)
            
            # Calculate final results
            end_time = time.time()
            time_taken = end_time - start_time if start_time else 0
            
            raw_wpm, net_wpm = self.calculate_wpm(len(text), time_taken, errors)
            accuracy = ((len(text) - errors) / len(text) * 100) if len(text) > 0 else 0
            
            # Display results
            self.show_cursor()
            self.display_results(net_wpm, raw_wpm, accuracy, errors, time_taken, difficulty)
            
            # Save to database
            if self.current_user_id and start_time:
                self.db.save_result(
                    self.current_user_id,
                    net_wpm,
                    accuracy,
                    raw_wpm,
                    errors,
                    difficulty,
                    int(time_taken)
                )
        
        except Exception as e:
            self.show_cursor()
            print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
    
    def display_results(self, net_wpm, raw_wpm, accuracy, errors, time_taken, difficulty):
        """Display test results"""
        self.clear_screen()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}╔{'═' * 58}╗{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}║{' ' * 20}TEST COMPLETE!{' ' * 24}║{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}╚{'═' * 58}╝{Colors.RESET}\n")
        
        print(f"{Colors.CYAN}{Colors.BOLD}Performance Metrics:{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
        print(f"  {Colors.BOLD}Net WPM:{Colors.RESET}           {Colors.GREEN}{Colors.BOLD}{net_wpm}{Colors.RESET}")
        print(f"  {Colors.BOLD}Raw WPM:{Colors.RESET}           {raw_wpm}")
        print(f"  {Colors.BOLD}Accuracy:{Colors.RESET}          {Colors.GREEN if accuracy >= 90 else Colors.YELLOW if accuracy >= 75 else Colors.RED}{accuracy:.2f}%{Colors.RESET}")
        print(f"  {Colors.BOLD}Errors:{Colors.RESET}            {Colors.RED}{errors}{Colors.RESET}")
        print(f"  {Colors.BOLD}Time:{Colors.RESET}              {time_taken:.2f} seconds")
        print(f"  {Colors.BOLD}Difficulty:{Colors.RESET}        {difficulty.upper()}")
        
        rating = self.get_rating(net_wpm, accuracy)
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Rating: {rating}{Colors.RESET}\n")
    
    def get_rating(self, wpm, accuracy):
        """Get performance rating"""
        if wpm >= 80 and accuracy >= 95:
            return "⭐⭐⭐⭐⭐ EXCELLENT!"
        elif wpm >= 60 and accuracy >= 90:
            return "⭐⭐⭐⭐ GREAT!"
        elif wpm >= 40 and accuracy >= 85:
            return "⭐⭐⭐ GOOD!"
        elif wpm >= 20 and accuracy >= 75:
            return "⭐⭐ KEEP PRACTICING!"
        else:
            return "⭐ NEEDS IMPROVEMENT!"
    
    def display_leaderboard(self, difficulty=None):
        """Display leaderboard"""
        self.clear_screen()
        
        title = f"🏆 {'GLOBAL' if not difficulty else difficulty.upper()} LEADERBOARD 🏆"
        print(f"\n{Colors.YELLOW}{Colors.BOLD}╔{'═' * 78}╗{Colors.RESET}")
        print(f"{Colors.YELLOW}{Colors.BOLD}║{title.center(78)}║{Colors.RESET}")
        print(f"{Colors.YELLOW}{Colors.BOLD}╚{'═' * 78}╝{Colors.RESET}\n")
        
        leaderboard = self.db.get_leaderboard(difficulty, 20)
        
        if not leaderboard:
            print(f"{Colors.RED}No data available yet. Be the first to take a test!{Colors.RESET}\n")
            return
        
        print(f"{Colors.CYAN}{Colors.BOLD}{'#':<5}{'Username':<20}{'WPM':<10}{'Accuracy':<12}{'Date':<20}{'Difficulty':<13}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 80}{Colors.RESET}")
        
        for idx, (username, wpm, accuracy, test_date, diff) in enumerate(leaderboard, 1):
            medal = ""
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            
            highlight = Colors.GREEN if username == self.username else Colors.WHITE
            date_str = test_date.strftime("%Y-%m-%d %H:%M")
            print(f"{highlight}{idx:<5}{username:<20}{wpm:<10.2f}{accuracy:<11.2f}%{date_str:<20}{diff:<13}{medal}{Colors.RESET}")
        
        print(f"\n{Colors.CYAN}{'─' * 80}{Colors.RESET}\n")
        
        if self.current_user_id:
            rank = self.db.get_user_rank(self.current_user_id, difficulty)
            if rank and rank > 20:
                print(f"{Colors.YELLOW}Your rank: #{rank}{Colors.RESET}\n")
    
    def display_user_stats(self):
        """Display user statistics"""
        if not self.current_user_id:
            return
        
        stats = self.db.get_user_stats(self.current_user_id)
        if not stats:
            print(f"{Colors.RED}No statistics available yet. Take a test first!{Colors.RESET}\n")
            return
        
        total_tests, avg_wpm, best_wpm, avg_accuracy, best_accuracy = stats
        
        self.clear_screen()
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}╔{'═' * 58}╗{Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}║{' ' * 18}YOUR STATISTICS{' ' * 25}║{Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}╚{'═' * 58}╝{Colors.RESET}\n")
        
        print(f"{Colors.CYAN}{Colors.BOLD}Username:{Colors.RESET} {self.username}")
        print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
        print(f"  {Colors.BOLD}Total Tests:{Colors.RESET}       {total_tests}")
        print(f"  {Colors.BOLD}Average WPM:{Colors.RESET}       {avg_wpm:.2f}")
        print(f"  {Colors.BOLD}Best WPM:{Colors.RESET}          {Colors.GREEN}{best_wpm:.2f}{Colors.RESET}")
        print(f"  {Colors.BOLD}Average Accuracy:{Colors.RESET}  {avg_accuracy:.2f}%")
        print(f"  {Colors.BOLD}Best Accuracy:{Colors.RESET}     {Colors.GREEN}{best_accuracy:.2f}%{Colors.RESET}")
        
        rank = self.db.get_user_rank(self.current_user_id)
        if rank:
            print(f"  {Colors.BOLD}Global Rank:{Colors.RESET}       {Colors.YELLOW}#{rank}{Colors.RESET}")
        
        print()
    
    def main_menu(self):
        """Display main menu"""
        while True:
            self.clear_screen()
            print(f"\n{Colors.BOLD}{Colors.CYAN}╔{'═' * 58}╗{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.CYAN}║{' ' * 17}SPEED TYPING TEST{' ' * 23}║{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.CYAN}╚{'═' * 58}╝{Colors.RESET}\n")
            
            if self.username:
                print(f"{Colors.GREEN}Logged in as: {self.username}{Colors.RESET}\n")
            
            print(f"{Colors.BOLD}Choose an option:{Colors.RESET}\n")
            print(f"  {Colors.CYAN}1.{Colors.RESET} Start Typing Test")
            print(f"  {Colors.CYAN}2.{Colors.RESET} View Leaderboard")
            print(f"  {Colors.CYAN}3.{Colors.RESET} View Your Statistics")
            print(f"  {Colors.CYAN}4.{Colors.RESET} Change Username")
            print(f"  {Colors.CYAN}5.{Colors.RESET} Exit")
            
            choice = input(f"\n{Colors.YELLOW}Enter your choice (1-5): {Colors.RESET}").strip()
            
            if choice == '1':
                self.difficulty_menu()
            elif choice == '2':
                self.leaderboard_menu()
            elif choice == '3':
                self.display_user_stats()
                input(f"\n{Colors.YELLOW}Press ENTER to continue...{Colors.RESET}")
            elif choice == '4':
                self.login()
            elif choice == '5':
                print(f"\n{Colors.GREEN}Thanks for using Speed Typing Test! Goodbye!{Colors.RESET}\n")
                break
            else:
                print(f"\n{Colors.RED}Invalid choice! Please try again.{Colors.RESET}")
                time.sleep(1)
    
    def difficulty_menu(self):
        """Display difficulty selection menu"""
        self.clear_screen()
        print(f"\n{Colors.BOLD}Select Difficulty:{Colors.RESET}\n")
        print(f"  {Colors.GREEN}1.{Colors.RESET} Easy")
        print(f"  {Colors.YELLOW}2.{Colors.RESET} Medium")
        print(f"  {Colors.MAGENTA}3.{Colors.RESET} Hard")
        print(f"  {Colors.RED}4.{Colors.RESET} Extreme")
        print(f"  {Colors.CYAN}5.{Colors.RESET} Back to Main Menu")
        
        choice = input(f"\n{Colors.YELLOW}Enter your choice (1-5): {Colors.RESET}").strip()
        
        difficulties = {
            '1': 'easy',
            '2': 'medium',
            '3': 'hard',
            '4': 'extreme'
        }
        
        if choice in difficulties:
            self.run_test_live(difficulties[choice])
            input(f"\n{Colors.YELLOW}Press ENTER to continue...{Colors.RESET}")
        elif choice != '5':
            print(f"\n{Colors.RED}Invalid choice!{Colors.RESET}")
            time.sleep(1)
    
    def leaderboard_menu(self):
        """Display leaderboard menu"""
        self.clear_screen()
        print(f"\n{Colors.BOLD}Select Leaderboard:{Colors.RESET}\n")
        print(f"  {Colors.CYAN}1.{Colors.RESET} Global (All Difficulties)")
        print(f"  {Colors.GREEN}2.{Colors.RESET} Easy")
        print(f"  {Colors.YELLOW}3.{Colors.RESET} Medium")
        print(f"  {Colors.MAGENTA}4.{Colors.RESET} Hard")
        print(f"  {Colors.RED}5.{Colors.RESET} Extreme")
        print(f"  {Colors.CYAN}6.{Colors.RESET} Back to Main Menu")
        
        choice = input(f"\n{Colors.YELLOW}Enter your choice (1-6): {Colors.RESET}").strip()

        difficulties = {
            '1': None,        # Global
            '2': 'easy',
            '3': 'medium',
            '4': 'hard',
            '5': 'extreme'
        }

        if choice in difficulties:
            self.display_leaderboard(difficulties[choice])
            input(f"\n{Colors.YELLOW}Press ENTER to continue...{Colors.RESET}")
        elif choice != '6':
            print(f"\n{Colors.RED}Invalid choice!{Colors.RESET}")
            time.sleep(1)

    def login(self):
        """Handle user login or registration"""
        self.clear_screen()
        print(f"\n{Colors.CYAN}{Colors.BOLD}╔{'═' * 58}╗{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}║{' ' * 20}LOGIN / SIGNUP{' ' * 25}║{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}╚{'═' * 58}╝{Colors.RESET}\n")
        
        username = input(f"{Colors.YELLOW}Enter your username: {Colors.RESET}").strip()
        if not username:
            print(f"{Colors.RED}Username cannot be empty!{Colors.RESET}")
            time.sleep(1)
            return
        
        if not self.db.connection:
            if not self.db.connect():
                print(f"{Colors.RED}Unable to connect to database. Starting in offline mode.{Colors.RESET}")
                time.sleep(1)
                self.current_user_id = None
                self.username = "Guest"
                return
        
        if self.db.create_tables():
            user_id = self.db.get_or_create_user(username)
            if user_id:
                self.current_user_id = user_id
                self.username = username
                print(f"\n{Colors.GREEN}Welcome, {username}!{Colors.RESET}")
                time.sleep(1)
            else:
                print(f"{Colors.RED}Error creating or fetching user.{Colors.RESET}")
                time.sleep(1)

    def start(self):
        """Start the typing test program"""
        self.clear_screen()
        print(f"\n{Colors.CYAN}{Colors.BOLD}Welcome to the Ultimate Speed Typing Test!{Colors.RESET}")
        print(f"{Colors.GRAY}-------------------------------------------{Colors.RESET}")
        input(f"\n{Colors.GREEN}Press ENTER to continue...{Colors.RESET}")
        
        self.login()
        self.main_menu()


if __name__ == "__main__":
    try:
        app = TypingTest()
        app.start()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Program exited by user.{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.RESET}")

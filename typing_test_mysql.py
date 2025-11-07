import time
import random
import os
import sys
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import winsound
import csv

try:
    if os.name == 'nt':
        import colorama
        colorama.init()
except Exception:
    pass

if os.name == 'nt':
    import msvcrt
    import winsound
else:
    import tty
    import termios

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
    @staticmethod
    def get_char():
        if os.name == 'nt':
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char == b'\xe0':
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
        else:
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
                        next_chars = sys.stdin.read(2)
                        return None
                    return char
                return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

class Database:
    def __init__(self):
        self.connection = None
    def connect(self):
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
    def delete_user_results(self, user_id):
        """Delete all test_results rows for a given user_id.

        Returns the number of deleted rows, or -1 on error.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM test_results WHERE user_id = %s", (user_id,))
            deleted = cursor.rowcount
            self.connection.commit()
            return deleted
        except Error as e:
            print(f"{Colors.RED}Error deleting user results: {e}{Colors.RESET}")
            return -1
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    # CSV support ---------------------------------------------------------
    def export_results_to_csv(self, filepath, difficulty=None, limit=None):
        """Export results to a CSV file. Returns number of rows written or -1 on error."""
        try:
            if not self.connection:
                if not self.connect():
                    print(f"{Colors.RED}Unable to connect to database for export.{Colors.RESET}")
                    return -1
            cursor = self.connection.cursor()
            if difficulty:
                query = (
                    "SELECT u.username, t.wpm, t.accuracy, t.raw_wpm, t.errors, t.difficulty, t.time_taken, t.test_date "
                    "FROM test_results t JOIN users u ON t.user_id = u.id WHERE t.difficulty = %s "
                    "ORDER BY t.test_date DESC"
                )
                params = (difficulty,)
            else:
                query = (
                    "SELECT u.username, t.wpm, t.accuracy, t.raw_wpm, t.errors, t.difficulty, t.time_taken, t.test_date "
                    "FROM test_results t JOIN users u ON t.user_id = u.id ORDER BY t.test_date DESC"
                )
                params = ()
            if limit:
                query += " LIMIT %s"
                params = params + (limit,)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                print(f"{Colors.YELLOW}No results to export.{Colors.RESET}")
                return 0
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['username','wpm','accuracy','raw_wpm','errors','difficulty','time_taken','test_date'])
                for r in rows:
                    # ensure datetime is string
                    row = list(r)
                    if isinstance(row[-1], datetime):
                        row[-1] = row[-1].strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow(row)
            print(f"{Colors.GREEN}Exported {len(rows)} rows to {filepath}{Colors.RESET}")
            return len(rows)
        except Exception as e:
            print(f"{Colors.RED}Error exporting CSV: {e}{Colors.RESET}")
            return -1



class TypingTest:
    def __init__(self):
        self.db = Database()
        self.current_user_id = None
        self.username = None
        self.keyboard = KeyboardInput()
    def play_error_beep(self):
        try:
            sound_file = os.path.join(os.path.dirname(__file__), 'click.wav')
            if os.path.exists(sound_file):
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.Beep(800, 200)  
        except:
            print('\a', end='', flush=True)
    def clear_screen(self):
        print('\033[H\033[J', end='', flush=True)
    def move_cursor(self, x, y):
        print(f"\033[{y};{x}H", end='', flush=True)
    def hide_cursor(self):
        print('\033[?25l', end='', flush=True)
    def show_cursor(self):
        print('\033[?25h', end='', flush=True)
    def load_text(self, difficulty):
        filename = f"text_{difficulty}.txt"
        if not os.path.exists(filename):
            alt = os.path.join("texts", filename)
            if os.path.exists(alt):
                filename = alt
            else:
                print(f"{Colors.RED}Error: {filename} not found!{Colors.RESET}")
                return None
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            paragraphs = [p for p in content.split('###PARA') if p.strip()]
            if not paragraphs:
                print(f"{Colors.RED}Error: No paragraphs found in {filename}!{Colors.RESET}")
                return None
            para_raw = random.choice(paragraphs).strip()
            para = para_raw.replace('\r\n', '\n').replace('\r', '\n')
            para = para.replace('  \n', '\n')
            lines = [line.rstrip() for line in para.split('\n')]
            para = '\n'.join(lines)
            para = para.strip('\n')
            return para
        except Exception as e:
            print(f"{Colors.RED}Error loading text: {e}{Colors.RESET}")
            return None
    def calculate_wpm(self, chars_typed, time_taken, errors):
        if time_taken <= 0:
            return 0, 0
        minutes = time_taken / 60
        gross_wpm = (chars_typed / 5) / minutes
        net_wpm = max(0, ((chars_typed / 5) - errors) / minutes)
        return round(gross_wpm, 2), round(net_wpm, 2)
    def wrap_text(self, text, width=80):
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
    def display_typing_interface(self, display_text, typed_text, errors, start_time, current_wpm):
        self.clear_screen()
        print(f"\n{Colors.CYAN}{Colors.BOLD}╔{'═' * 78}╗{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}║{' ' * 28}TYPING TEST{' ' * 39}║{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}╚{'═' * 78}╝{Colors.RESET}\n")
        elapsed = time.time() - start_time if start_time else 0
        correct_chars = len(typed_text) - errors
        accuracy = (correct_chars / max(len(typed_text), 1) * 100) if typed_text else 100
        stats = f"  WPM: {Colors.GREEN}{current_wpm}{Colors.RESET}  |  "
        stats += f"Accuracy: {Colors.GREEN if accuracy >= 95 else Colors.YELLOW if accuracy >= 85 else Colors.RED}{accuracy:.1f}%{Colors.RESET}  |  "
        stats += f"Errors: {Colors.RED}{errors}{Colors.RESET}  |  "
        stats += f"Time: {Colors.CYAN}{elapsed:.1f}s{Colors.RESET}"
        print(stats)
        print(f"{Colors.CYAN}{'─' * 80}{Colors.RESET}\n")
        typed_len = len(typed_text)
        non_newline_idx = 0
        out_lines = []
        current_line = ""
        for ch in display_text:
            if ch == '\n':
                out_lines.append(current_line)
                current_line = ""
                continue
            color_char = None
            if non_newline_idx < typed_len:
                typed_char = typed_text[non_newline_idx]
                if typed_char == ch:
                    color_char = f"{Colors.GREEN}{ch}{Colors.RESET}"
                else:
                    color_char = f"{Colors.RED}{Colors.BOLD}{ch}{Colors.RESET}"
            elif non_newline_idx == typed_len:
                color_char = f"{Colors.YELLOW}{Colors.UNDERLINE}{ch}{Colors.RESET}"
            else:
                color_char = f"{Colors.GRAY}{ch}{Colors.RESET}"
            current_line += color_char
            non_newline_idx += 1
        out_lines.append(current_line)
        for ln in out_lines:
            print(ln)
        print(f"\n{Colors.CYAN}{'─' * 80}{Colors.RESET}")
        print(f"{Colors.DIM}ESC to quit | Backspace to correct | Type to continue{Colors.RESET}\n")
    def run_test_live(self, difficulty):
        display_text = self.load_text(difficulty)
        if not display_text:
            return
        expected_chars = [ch for ch in display_text if ch != '\n']
        expected_len = len(expected_chars)
        print(f"\n{Colors.GREEN}{Colors.BOLD}Get ready to type!{Colors.RESET}")
        print(f"\n{Colors.CYAN}Difficulty: {difficulty.upper()}{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Paragraph will appear below. Type continuously — you do NOT need to press ENTER at line ends.{Colors.RESET}")
        print(f"{Colors.YELLOW}• Correct characters will turn {Colors.GREEN}GREEN{Colors.RESET}")
        print(f"{Colors.YELLOW}• Wrong characters will turn {Colors.RED}RED{Colors.RESET}")
        print(f"{Colors.YELLOW}• The current character to type is {Colors.YELLOW}{Colors.UNDERLINE}HIGHLIGHTED{Colors.RESET}")
        print(f"\n{Colors.BOLD}Text preview:{Colors.RESET}\n")
        for line in display_text.split('\n'):
            print(f"{Colors.GRAY}{line}{Colors.RESET}")
        input(f"\n{Colors.GREEN}Press ENTER when ready...{Colors.RESET}")
        typed_text = ""
        errors = 0
        start_time = None
        current_wpm = 0
        last_update = 0
        self.hide_cursor()
        try:
            while len(typed_text) < expected_len:
                self.display_typing_interface(display_text, typed_text, errors, start_time, current_wpm)
                char = None
                while char is None:
                    char = self.keyboard.get_char()
                    time.sleep(0.01)
                    # Only update WPM every second instead of every 0.5 seconds
                    if start_time and time.time() - last_update > 1.0:
                        elapsed = time.time() - start_time
                        _, current_wpm = self.calculate_wpm(len(typed_text), elapsed, errors)
                        last_update = time.time()
                        # Only refresh display when WPM updates
                        self.display_typing_interface(display_text, typed_text, errors, start_time, current_wpm)
                if start_time is None and char not in ['\b', '\x1b']:
                    start_time = time.time()
                    last_update = start_time
                if char == '\x1b':
                    self.show_cursor()
                    print(f"\n\n{Colors.RED}Test cancelled!{Colors.RESET}")
                    return
                if char in ('\b', '\x7f'):
                    if len(typed_text) > 0:
                        last_index = len(typed_text) - 1
                        if typed_text[last_index] != expected_chars[last_index]:
                            errors = max(0, errors - 1)
                        typed_text = typed_text[:-1]
                    continue
                if char == '\r':
                    char = '\n'
                if char == '\n':
                    char = ' '
                typed_text += char
                idx = len(typed_text) - 1
                if idx < expected_len:
                    expected_char = expected_chars[idx]
                    if char != expected_char:
                        self.play_error_beep()
                        errors += 1
                else:
                    pass
                # Only update display when character is typed, not on a timer
                self.display_typing_interface(display_text, typed_text, errors, start_time, current_wpm)
            self.display_typing_interface(display_text, typed_text, errors, start_time, current_wpm)
            time.sleep(0.6)
            end_time = time.time()
            time_taken = end_time - start_time if start_time else 0
            raw_wpm, net_wpm = self.calculate_wpm(len(expected_chars), time_taken, errors)
            accuracy = ((len(expected_chars) - errors) / len(expected_chars) * 100) if len(expected_chars) > 0 else 0
            self.show_cursor()
            self.display_results(net_wpm, raw_wpm, accuracy, errors, time_taken, difficulty)
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
    def clear_history(self):
        """Prompt the user to confirm and clear their test history (all test_results rows).

        Confirmation requires typing the current username to avoid accidents.
        """
        if not self.current_user_id:
            print(f"{Colors.RED}No user logged in. Please login first.{Colors.RESET}")
            time.sleep(1)
            return
        if not self.db.connection:
            if not self.db.connect():
                print(f"{Colors.RED}Unable to connect to database. Try again later.{Colors.RESET}")
                time.sleep(1)
                return
        prompt = input(f"{Colors.YELLOW}Type your username ({self.username}) to confirm clearing ALL your test history, or type CANCEL to abort: {Colors.RESET}").strip()
        if prompt != self.username:
            print(f"{Colors.RED}Confirmation failed — history not cleared.{Colors.RESET}")
            time.sleep(1)
            return
        deleted = self.db.delete_user_results(self.current_user_id)
        if deleted >= 0:
            print(f"{Colors.GREEN}Successfully deleted {deleted} test result(s) from your history.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to delete history. See error above.{Colors.RESET}")
        time.sleep(1)
    def main_menu(self):
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
            print(f"  {Colors.CYAN}5.{Colors.RESET} Clear History")
            print(f"  {Colors.CYAN}6.{Colors.RESET} Export Results to CSV")
            print(f"  {Colors.CYAN}7.{Colors.RESET} Exit")
            choice = input(f"\n{Colors.YELLOW}Enter your choice (1-7): {Colors.RESET}").strip()
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
                self.clear_history()
            elif choice == '6':
                # Export results
                path = input(f"{Colors.YELLOW}Enter output CSV filepath (e.g. results.csv): {Colors.RESET}").strip()
                if not path:
                    print(f"{Colors.RED}No filepath provided.{Colors.RESET}")
                    time.sleep(1)
                else:
                    diff = input(f"{Colors.YELLOW}Filter by difficulty (easy/medium/hard/extreme) or leave blank for ALL: {Colors.RESET}").strip() or None
                    if diff == '':
                        diff = None
                    self.db.export_results_to_csv(path, difficulty=diff)
                    input(f"\n{Colors.YELLOW}Press ENTER to continue...{Colors.RESET}")
            elif choice == '7':
                print(f"\n{Colors.GREEN}Thanks for using Speed Typing Test! Goodbye!{Colors.RESET}\n")
                break
            else:
                print(f"\n{Colors.RED}Invalid choice! Please try again.{Colors.RESET}")
                time.sleep(1)
    def difficulty_menu(self):
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
            '1': None,
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
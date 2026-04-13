import sys
import numpy as np
import random
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from sklearn.ensemble import RandomForestClassifier

# ================= DATABASE =================

conn = sqlite3.connect("game.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    result TEXT,
    difficulty TEXT
)
""")

conn.commit()


def register_user(u, p):
    try:
        cur.execute("INSERT INTO users VALUES (?,?)", (u, p))
        conn.commit()
        return True
    except:
        return False


def login_user(u, p):
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    return cur.fetchone()


def save_result(user, result, diff):
    cur.execute("INSERT INTO history(username,result,difficulty) VALUES (?,?,?)",
                (user, result, diff))
    conn.commit()


def get_stats(user):
    cur.execute("SELECT result,difficulty FROM history WHERE username=?", (user,))
    return cur.fetchall()


# ================= GAME LOGIC =================

def check_win(b, p):
    b = b.reshape(3, 3)

    for i in range(3):
        if all(b[i, j] == p for j in range(3)): return True
        if all(b[j, i] == p for j in range(3)): return True

    if b[0, 0] == b[1, 1] == b[2, 2] == p: return True
    if b[0, 2] == b[1, 1] == b[2, 0] == p: return True

    return False


def available(b):
    return np.where(b == 0)[0]


# ================= RULE AI =================

def best_rule(board):
    empty = available(board)

    for m in empty:
        t = board.copy()
        t[m] = 2
        if check_win(t, 2):
            return m

    for m in empty:
        t = board.copy()
        t[m] = 1
        if check_win(t, 1):
            return m

    if 4 in empty:
        return 4

    return random.choice(empty)


# ================= ML =================

def generate_data(n=3000):
    X, y = [], []

    for _ in range(n):
        board = np.zeros(9)

        for _ in range(random.randint(1, 5)):
            e = available(board)
            if len(e) == 0:
                break
            board[random.choice(e)] = 1

        e = available(board)
        if len(e) == 0:
            continue

        X.append(board.copy())
        y.append(best_rule(board))

    return np.array(X), np.array(y)


X, y = generate_data()
model = RandomForestClassifier(n_estimators=120)
model.fit(X, y)


# ================= MINIMAX =================

def minimax(board, is_max):
    empty = available(board)

    if check_win(board, 2): return 1
    if check_win(board, 1): return -1
    if len(empty) == 0: return 0

    if is_max:
        best = -999
        for m in empty:
            board[m] = 2
            best = max(best, minimax(board, False))
            board[m] = 0
        return best
    else:
        best = 999
        for m in empty:
            board[m] = 1
            best = min(best, minimax(board, True))
            board[m] = 0
        return best


def best_minimax(board):
    empty = available(board)
    best_score = -999
    move = None

    for m in empty:
        board[m] = 2
        score = minimax(board, False)
        board[m] = 0

        if score > best_score:
            best_score = score
            move = m

    return move


# ================= AI =================

def ai_move(board, diff):

    empty = available(board)
    if len(empty) == 0:
        return

    if diff == "Easy":
        board[random.choice(empty)] = 2
        return

    pred = model.predict([board])[0]

    if diff == "Medium":
        if pred in empty:
            board[pred] = 2
        else:
            board[best_rule(board)] = 2
        return

    move = best_minimax(board)
    if move is not None:
        board[move] = 2


# ================= LOGIN UI =================

class Login(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.setStyleSheet("""
            QWidget { background-color: #1e1e2f; color: white; }
            QLineEdit { padding: 10px; border-radius: 8px; }
            QPushButton { background-color: #3b82f6; padding: 10px; border-radius: 8px; }
            QPushButton:hover { background-color: #2563eb; }
        """)

        layout = QVBoxLayout()

        title = QLabel("TIC TAC TOE LOGIN")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.u = QLineEdit()
        self.u.setPlaceholderText("Username")

        self.p = QLineEdit()
        self.p.setPlaceholderText("Password")
        self.p.setEchoMode(QLineEdit.Password)

        login = QPushButton("Login")
        signup = QPushButton("Signup")

        login.clicked.connect(self.login)
        signup.clicked.connect(self.signup)

        layout.addWidget(title)
        layout.addWidget(self.u)
        layout.addWidget(self.p)
        layout.addWidget(login)
        layout.addWidget(signup)

        self.setLayout(layout)

    def login(self):
        if login_user(self.u.text(), self.p.text()):
            self.parent.user = self.u.text()
            self.parent.setCurrentIndex(1)
        else:
            QMessageBox.warning(self, "Error", "Invalid login")

    def signup(self):
        if register_user(self.u.text(), self.p.text()):
            QMessageBox.information(self, "OK", "Account created")
        else:
            QMessageBox.warning(self, "Error", "User exists")


# ================= GAME UI =================

class Game(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.board = np.zeros(9)
        self.diff = "Medium"

        self.setStyleSheet("""
            QWidget { background-color: #111827; color: white; }
            QPushButton {
                background-color: #374151;
                color: white;
                font-size: 18px;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)

        layout = QVBoxLayout()

        self.combo = QComboBox()
        self.combo.addItems(["Easy", "Medium", "Hard"])
        self.combo.setStyleSheet("padding:8px;")
        self.combo.currentTextChanged.connect(self.set_diff)

        layout.addWidget(self.combo)

        self.grid = QGridLayout()
        self.btns = []

        for i in range(9):
            b = QPushButton("")
            b.setFixedSize(90, 90)
            b.clicked.connect(lambda _, x=i: self.play(x))
            self.btns.append(b)
            self.grid.addWidget(b, i // 3, i % 3)

        layout.addLayout(self.grid)

        stats = QPushButton("SHOW STATS")
        stats.clicked.connect(self.show_stats)

        reset = QPushButton("RESET")
        reset.clicked.connect(self.reset)

        layout.addWidget(stats)
        layout.addWidget(reset)

        self.setLayout(layout)

    def set_diff(self, d):
        self.diff = d

    def play(self, i):
        if self.board[i] != 0:
            return

        self.board[i] = 1
        self.btns[i].setText("X")

        if check_win(self.board, 1):
            save_result(self.parent.user, "win", self.diff)
            QMessageBox.information(self, "Result", "You Win!")
            self.reset()
            return

        ai_move(self.board, self.diff)

        for i in range(9):
            if self.board[i] == 2:
                self.btns[i].setText("O")

        if check_win(self.board, 2):
            save_result(self.parent.user, "loss", self.diff)
            QMessageBox.information(self, "Result", "AI Wins!")
            self.reset()
            return

        if len(available(self.board)) == 0:
            save_result(self.parent.user, "draw", self.diff)
            QMessageBox.information(self, "Result", "Draw!")
            self.reset()

    def reset(self):
        self.board[:] = 0
        for b in self.btns:
            b.setText("")

    def show_stats(self):
        data = get_stats(self.parent.user)

        msg = "YOUR PERFORMANCE\n\n"
        for r, d in data:
            msg += f"{r.upper()} - {d}\n"

        QMessageBox.information(self, "Stats", msg)


# ================= MAIN APP =================

class App(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.user = ""

        self.login = Login(self)
        self.game = Game(self)

        self.addWidget(self.login)
        self.addWidget(self.game)


# ================= RUN =================

app = QApplication(sys.argv)
window = App()
window.setWindowTitle("A+ ML Tic Tac Toe")
window.resize(320, 450)
window.show()
sys.exit(app.exec())
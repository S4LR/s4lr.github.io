# server.py
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import threading
import logging
from datetime import datetime

# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ultimate-chat-server")

# -----------------------------
# Database Setup
# -----------------------------
DB_FILE = "chat.db"
lock = threading.Lock()

def init_db():
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                created_at TEXT
            )
        """)
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                recipient TEXT,
                encrypted TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI(title="Ultimate Encrypted Chat Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict later if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Data Models
# -----------------------------
class User(BaseModel):
    username: str

class Message(BaseModel):
    sender: str
    recipient: str
    encrypted: str

# -----------------------------
# Helper Functions
# -----------------------------
def user_exists(username: str) -> bool:
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

def add_user(username: str):
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(username, created_at) VALUES (?, ?)",
            (username, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

def store_message(sender: str, recipient: str, encrypted: str):
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages(sender, recipient, encrypted, timestamp) VALUES (?, ?, ?, ?)",
            (sender, recipient, encrypted, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

def fetch_messages(recipient: str):
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, sender, encrypted, timestamp FROM messages WHERE recipient = ?",
            (recipient,)
        )
        rows = cursor.fetchall()
        # Delete messages after fetching
        ids = [str(row[0]) for row in rows]
        if ids:
            cursor.execute(f"DELETE FROM messages WHERE id IN ({','.join(ids)})")
            conn.commit()
        conn.close()
        return [{"sender": r[1], "encrypted": r[2], "timestamp": r[3]} for r in rows]

# -----------------------------
# Routes / Endpoints
# -----------------------------

# Friendly root page
@app.get("/", response_class=HTMLResponse)
def root_html():
    return """
    <html>
        <head><title>Ultimate Chat Server</title></head>
        <body style="font-family:sans-serif; text-align:center; margin-top:50px;">
            <h1>Server is UP! 🚀</h1>
            <p>You can connect to it using the API endpoints:</p>
            <ul style="list-style:none;">
                <li><strong>/register</strong> - Register a user</li>
                <li><strong>/send_message</strong> - Send encrypted message</li>
                <li><strong>/get_messages/&lt;username&gt;</strong> - Get your messages</li>
            </ul>
            <p>Happy chatting!</p>
        </body>
    </html>
    """

# Register new user
@app.post("/register")
def register(user: User):
    if not user.username:
        raise HTTPException(status_code=400, detail="Username required")
    if user_exists(user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    add_user(user.username)
    logger.info(f"New user registered: {user.username}")
    return {"status": "ok", "username": user.username}

# Send a message
@app.post("/send_message")
def send_message_endpoint(msg: Message):
    if not (msg.sender and msg.recipient and msg.encrypted):
        raise HTTPException(status_code=400, detail="All fields are required")
    if not user_exists(msg.sender) or not user_exists(msg.recipient):
        raise HTTPException(status_code=400, detail="Sender or recipient does not exist")
    store_message(msg.sender, msg.recipient, msg.encrypted)
    logger.info(f"Message stored: {msg.sender} -> {msg.recipient}")
    return {"status": "ok"}

# Get messages for a recipient
@app.get("/get_messages/{recipient}")
def get_messages_endpoint(recipient: str):
    if not user_exists(recipient):
        raise HTTPException(status_code=400, detail="Recipient does not exist")
    messages = fetch_messages(recipient)
    return {"messages": messages, "count": len(messages)}

# Optional admin endpoint to view all users
@app.get("/all_users")
def all_users():
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT username, created_at FROM users")
        rows = cursor.fetchall()
        conn.close()
        return {"users": [{"username": r[0], "created_at": r[1]} for r in rows], "count": len(rows)}

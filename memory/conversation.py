import sqlite3
from pathlib import Path
from datetime import datetime


# -----------------------------
# Configuration
# -----------------------------

DB_PATH = Path("data/conversations.db")


# -----------------------------
# Database connection
# -----------------------------

def get_connection():
    DB_PATH.parent.mkdir(
        exist_ok=True
    )

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# -----------------------------
# Initialize database
# -----------------------------

def initialize_memory():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_conversation_id
        ON conversations(conversation_id)
    """)

    connection.commit()
    connection.close()


# -----------------------------
# Save message
# -----------------------------

def save_message(
    conversation_id,
    role,
    content
):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO conversations (
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
            datetime.utcnow().isoformat()
        )
    )

    connection.commit()
    connection.close()


# -----------------------------
# Get conversation history
# -----------------------------

def get_conversation_history(
    conversation_id,
    limit=10
):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT role, content, created_at
        FROM conversations
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            conversation_id,
            limit
        )
    ).fetchall()

    connection.close()

    # Reverse so the oldest message
    # comes first.
    rows = list(reversed(rows))

    return [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# -----------------------------
# Clear conversation
# -----------------------------

def clear_conversation(
    conversation_id
):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM conversations
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()
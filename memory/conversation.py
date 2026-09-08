import sqlite3

from pathlib import Path
from datetime import datetime


DB_PATH = Path("data/conversations.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def initialize_memory():

    connection = get_connection()

    # Conversation threads
    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversation_threads (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conversation_id TEXT UNIQUE NOT NULL,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL

        )
    """)

    # Messages
    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conversation_id TEXT NOT NULL,

            role TEXT NOT NULL,

            content TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_messages_conversation_id
        ON messages(conversation_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_conversation_threads_user_id
        ON conversation_threads(user_id)
    """)

    connection.commit()
    connection.close()


# ==========================================
# CREATE CONVERSATION
# ==========================================

def create_conversation(
    conversation_id,
    user_id,
    title="New conversation"
):

    connection = get_connection()

    now = datetime.utcnow().isoformat()

    connection.execute(
        """
        INSERT INTO conversation_threads (
            conversation_id,
            user_id,
            title,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            user_id,
            title,
            now,
            now
        )
    )

    connection.commit()
    connection.close()


# ==========================================
# GET USER CONVERSATIONS
# ==========================================

def get_user_conversations(user_id):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            conversation_id,
            title,
            created_at,
            updated_at

        FROM conversation_threads

        WHERE user_id = ?

        ORDER BY updated_at DESC
        """
        ,
        (user_id,)
    ).fetchall()

    connection.close()

    return [
        {
            "conversation_id": row["conversation_id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        for row in rows
    ]


# ==========================================
# GET SINGLE CONVERSATION
# ==========================================

def get_conversation(
    conversation_id,
    user_id
):

    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            conversation_id,
            title,
            created_at,
            updated_at

        FROM conversation_threads

        WHERE conversation_id = ?

        AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    ).fetchone()

    connection.close()

    if not row:
        return None

    return {
        "conversation_id": row["conversation_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    }


# ==========================================
# UPDATE TITLE
# ==========================================

def update_conversation_title(
    conversation_id,
    user_id,
    title
):

    connection = get_connection()

    connection.execute(
        """
        UPDATE conversation_threads

        SET
            title = ?,
            updated_at = ?

        WHERE conversation_id = ?

        AND user_id = ?
        """,
        (
            title,
            datetime.utcnow().isoformat(),
            conversation_id,
            user_id
        )
    )

    connection.commit()
    connection.close()


# ==========================================
# TOUCH CONVERSATION
# ==========================================

def touch_conversation(
    conversation_id
):

    connection = get_connection()

    connection.execute(
        """
        UPDATE conversation_threads

        SET updated_at = ?

        WHERE conversation_id = ?
        """,
        (
            datetime.utcnow().isoformat(),
            conversation_id
        )
    )

    connection.commit()
    connection.close()


# ==========================================
# SAVE MESSAGE
# ==========================================

def save_message(
    conversation_id,
    role,
    content
):

    connection = get_connection()

    now = datetime.utcnow().isoformat()

    connection.execute(
        """
        INSERT INTO messages (
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
            now
        )
    )

    connection.execute(
        """
        UPDATE conversation_threads

        SET updated_at = ?

        WHERE conversation_id = ?
        """,
        (
            now,
            conversation_id
        )
    )

    connection.commit()
    connection.close()


# ==========================================
# GET CONVERSATION HISTORY
# ==========================================

def get_conversation_history(
    conversation_id,
    limit=50
):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            role,
            content,
            created_at

        FROM messages

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

    rows = list(reversed(rows))

    return [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# ==========================================
# DELETE CONVERSATION
# ==========================================

def delete_conversation(
    conversation_id,
    user_id
):

    connection = get_connection()

    # Delete messages belonging to this conversation
    # only if the conversation belongs to the user.
    connection.execute(
        """
        DELETE FROM messages

        WHERE conversation_id = ?

        AND EXISTS (
            SELECT 1

            FROM conversation_threads

            WHERE conversation_threads.conversation_id = ?

            AND conversation_threads.user_id = ?
        )
        """,
        (
            conversation_id,
            conversation_id,
            user_id
        )
    )

    # Delete conversation itself
    connection.execute(
        """
        DELETE FROM conversation_threads

        WHERE conversation_id = ?

        AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    )

    connection.commit()
    connection.close()


# ==========================================
# CLEAR MESSAGES
# ==========================================

def clear_conversation(
    conversation_id
):

    connection = get_connection()

    connection.execute(
        """
        DELETE FROM messages

        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    connection.commit()
    connection.close()
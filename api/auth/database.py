
import sqlite3
from pathlib import Path


DB_PATH = Path("data/users.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_users_database():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def create_user(full_name, email, password_hash, created_at):

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO users (
            full_name,
            email,
            password_hash,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            full_name,
            email,
            password_hash,
            created_at
        )
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id


def get_user_by_email(email):

    connection = get_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    connection.close()

    return user

def get_user_by_id(user_id):

    connection = get_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return user
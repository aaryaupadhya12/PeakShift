import sqlite3
import pytest

def test_credits_column_creation():
    # Setup: create legacy DB without credits column
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (username TEXT PRIMARY KEY)")
    cur.execute("INSERT INTO users (username) VALUES (?)", ("volunteer",))
    # Simulate approval logic that adds credits column if missing
    try:
        cur.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Already exists
    cur.execute("UPDATE users SET credits = COALESCE(credits, 0) + 1 WHERE username = ?", ("volunteer",))
    conn.commit()
    credits = cur.execute("SELECT credits FROM users WHERE username = ?", ("volunteer",)).fetchone()[0]
    assert credits == 1
    conn.close()

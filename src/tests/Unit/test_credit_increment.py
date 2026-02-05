import sqlite3
import pytest

def test_credit_increment():
    # Setup: create in-memory DB with credits column
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (username TEXT PRIMARY KEY, credits INTEGER DEFAULT 0)")
    cur.execute("INSERT INTO users (username, credits) VALUES (?, ?)", ("volunteer", 0))
    # Simulate approval logic
    cur.execute("UPDATE users SET credits = credits + 1 WHERE username = ?", ("volunteer",))
    conn.commit()
    credits = cur.execute("SELECT credits FROM users WHERE username = ?", ("volunteer",)).fetchone()[0]
    assert credits == 1
    conn.close()

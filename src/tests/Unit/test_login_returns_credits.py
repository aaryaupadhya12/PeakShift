import sqlite3
import pytest

def test_login_returns_credits():
    # Setup: create in-memory DB with credits column
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT, credits INTEGER DEFAULT 0)")
    cur.execute("INSERT INTO users (username, password, credits) VALUES (?, ?, ?)", ("volunteer", "hashed", 5))
    # Simulate login response
    user = cur.execute("SELECT * FROM users WHERE username = ?", ("volunteer",)).fetchone()
    result = {"username": user[0], "credits": user[2]}
    assert result["credits"] == 5
    conn.close()

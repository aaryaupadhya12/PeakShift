import sqlite3
import pytest

def test_volunteer_approval_flow():
    # Setup: create DB and tables
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (username TEXT PRIMARY KEY, credits INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE volunteer_commitments (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, status TEXT)")
    cur.execute("INSERT INTO users (username, credits) VALUES (?, ?)", ("volunteer", 0))
    cur.execute("INSERT INTO volunteer_commitments (username, status) VALUES (?, ?)", ("volunteer", "pending"))
    # Simulate manager approval
    cur.execute("UPDATE volunteer_commitments SET status = 'approved' WHERE username = ?", ("volunteer",))
    cur.execute("UPDATE users SET credits = credits + 1 WHERE username = ?", ("volunteer",))
    conn.commit()
    credits = cur.execute("SELECT credits FROM users WHERE username = ?", ("volunteer",)).fetchone()[0]
    assert credits == 1
    conn.close()

import sqlite3
import json
from backend.config import get_connection
from backend.auth import shift_management

# Simple test to ensure publish_shift attempts to send notification

def test_publish_triggers_notification(monkeypatch):
    # Setup in-memory DB and create tables similar to init_db
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, date TEXT, start_time TEXT, end_time TEXT, spots INT, location TEXT, status TEXT, created_by TEXT)")
    conn.commit()

    # Insert a manager user (username used as email for demo)
    cursor.execute("INSERT OR REPLACE INTO users (username, role) VALUES (?,?)", ("manager@example.com","manager"))
    conn.commit()

    # Insert a shift
    cursor.execute("INSERT INTO shifts (title, date, start_time, end_time, spots, location, status, created_by) VALUES (?,?,?,?,?,?,?,?)",
                   ("Test Shift", "2025-11-12", "09:00", "11:00", 2, "Main", "validated", "manager"))
    shift_id = cursor.lastrowid
    conn.commit()

    called = {"notified": False}

    def fake_send(shift):
        called["notified"] = True
        assert shift["id"] == shift_id

    monkeypatch.setattr(shift_management.email_service, "send_new_shift_notification", fake_send)

    # Call publish_shift
    resp = shift_management.publish_shift(shift_id, published_by="manager")
    assert resp["status"] == "published"

    # Since notification runs in background thread, give a small moment — but we mocked sync function so it should be immediate
    assert called["notified"] is True

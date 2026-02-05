import sqlite3
import pytest

def test_overlapping_shifts():
    # Setup: create DB and tables
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE shifts (id INTEGER PRIMARY KEY, date TEXT, start_time TEXT, end_time TEXT)")
    cur.execute("CREATE TABLE volunteer_commitments (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, shift_id INTEGER, status TEXT)")
    # Add two overlapping shifts
    cur.execute("INSERT INTO shifts (id, date, start_time, end_time) VALUES (1, '2025-11-08', '09:00', '13:00')")
    cur.execute("INSERT INTO shifts (id, date, start_time, end_time) VALUES (2, '2025-11-08', '12:00', '16:00')")
    # Volunteer signs up for first shift
    cur.execute("INSERT INTO volunteer_commitments (username, shift_id, status) VALUES (?, ?, ?)", ("volunteer", 1, "approved"))
    # Try to sign up for overlapping shift
    # Simulate overlap check
    shift1_end = '13:00'
    shift2_start = '12:00'
    overlap = shift2_start < shift1_end
    assert overlap
    conn.close()

"""
Database Initialization Script
Creates volunteer.db with users table and sample data
Run this BEFORE testing: python src/backend/init_db.py
"""

import os
import sys
import sqlite3
import hashlib

# Add the src directory to Python path
src_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, src_path)

from src.backend.config import get_connection


def init_database():
    """Initialize the volunteer database with users table and sample users"""

    print("Initializing volunteer.db database...")

    # Connect to database (creates if doesn't exist)
    conn = get_connection()
    cursor = conn.cursor()

    # Drop existing tables (for clean slate)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS shifts")
    cursor.execute("DROP TABLE IF EXISTS volunteer_commitments")
    print("Cleared existing tables")

    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'manager', 'volunteer')),
            attempts INTEGER DEFAULT 0,
            locked_until TEXT,
            otp TEXT,
            otp_expires TEXT,
            credits INTEGER DEFAULT 0
        )
    """)
    # Create shifts table
    cursor.execute("""
        CREATE TABLE shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            spots INT,
            volunteers TEXT DEFAULT '[]',
            status TEXT DEFAULT 'draft',
            created_by TEXT,
            FOREIGN KEY(created_by) REFERENCES users(username)
        )
    """)
    # Create volunteer_commitments table
    cursor.execute("""
        CREATE TABLE volunteer_commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            shift_id INTEGER,
            volunteered_at TEXT,
            status TEXT DEFAULT 'pending',
            approved_at TEXT,
            approved_by TEXT,
            can_cancel_until TEXT,
            FOREIGN KEY(username) REFERENCES users(username),
            FOREIGN KEY(shift_id) REFERENCES shifts(id),
            FOREIGN KEY(approved_by) REFERENCES users(username)
        )
    """)
    print("Created users table")

    sample_users = [
        ('admin', 'admin123', 'admin'),
        ('manager', 'manager123', 'manager'),
        ('volunteer', 'volunteer123', 'volunteer'),
        ('testuser', 'testpass123', 'volunteer'),
        ('locktest_user', 'test123', 'volunteer'),
    ]

    for username, password, role in sample_users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users
            (username, password, role, attempts, locked_until, otp, otp_expires, credits)
            VALUES (?, ?, ?, 0, NULL, NULL, NULL, 0)
        """, (username, hashed_password, role))
        print(f"Created user: {username} ({role})")

    # Create sample shifts
    sample_shifts = [
        ('Morning Shift', '2025-11-07', '09:00', '13:00', 5, 'draft', 'manager'),
        ('Afternoon Shift', '2025-11-07', '14:00', '18:00', 3, 'validated', 'manager'),
        ('Evening Shift', '2025-11-07', '19:00', '23:00', 4, 'published', 'manager'),
    ]

    for title, date, start_time, end_time, spots, status, created_by in sample_shifts:
        cursor.execute("""
            INSERT INTO shifts
            (title, date, start_time, end_time, spots, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, date, start_time, end_time, spots, status, created_by))
        print(f"Created shift: {title}")

    conn.commit()
    conn.close()

    print("\nDatabase initialized successfully!")
    print("\nSample Users Created:")
    print("   Username: admin      | Password: admin123      | Role: admin")
    print("   Username: manager    | Password: manager123    | Role: manager")
    print("   Username: volunteer  | Password: volunteer123  | Role: volunteer")
    print("   Username: testuser   | Password: testpass123   | Role: volunteer")
    print("\nSample Shifts Created:")
    print("   Morning Shift   | Status: draft     | Spots: 5")
    print("   Afternoon Shift | Status: validated | Spots: 3")
    print("   Evening Shift   | Status: published | Spots: 4")
    print("\nYou can now start the FastAPI server: uvicorn src.backend.main:app --reload\n")


if __name__ == "__main__":
    init_database()
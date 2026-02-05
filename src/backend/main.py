"""Main FastAPI application for Helping Hands.

Configures middleware, database initialization and registers routers.
"""

import hashlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_connection

from backend.auth.user_login import router as login_router
from backend.auth.two_factor_auth import router as twofa_router
from backend.auth.user_lockout import router as lockout_router
from backend.auth.role_based_access import router as rbac_router
from backend.auth.shift_management import router as shift_router
from backend.auth.manager_reports import router as reports_router


app = FastAPI(title="Helping Hands API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)




def init_db():
    """Create tables if they do not exist (safe for repeated calls)."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Users Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT CHECK(role IN ('admin', 'manager', 'volunteer')),
            attempts INT DEFAULT 0,
            locked_until TEXT,
            otp TEXT,
            otp_expires TEXT,
            credits INTEGER DEFAULT 0
        )
    """)

    # --- Shifts Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            spots INT,
            location TEXT,
            volunteers TEXT DEFAULT '[]',
            status TEXT DEFAULT 'draft',
            created_by TEXT
        )
    """)

    # --- Volunteer Commitments ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volunteer_commitments (
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

    # --- Default Admin User (only if not already exists) ---
    admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password, role, attempts, locked_until, otp, otp_expires)
        VALUES (?, ?, ?, 0, NULL, NULL, NULL)
    """, ('admin', admin_password, 'admin'))

    # --- Add missing columns if they don't exist (migrations) ---
    try:
        # Check if credits column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'credits' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0")
            print("Added 'credits' column to users table")
    except Exception as e:
        print(f"Note: Could not add credits column: {e}")

    try:
        # Check if location column exists in shifts table
        cursor.execute("PRAGMA table_info(shifts)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'location' not in columns:
            cursor.execute("ALTER TABLE shifts ADD COLUMN location TEXT DEFAULT 'Default Location'")
            print("Added 'location' column to shifts table")
    except Exception as e:
        print(f"Note: Could not add location column: {e}")

    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event():
    """
    Initialize DB on startup — always initialize to ensure tables exist
    """
    print("Initializing database schema...")
    init_db()
    print("Database initialization complete")


# --------------------------------------------------
# ROUTER REGISTRATION
# --------------------------------------------------
app.include_router(login_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(twofa_router, prefix="/api/auth", tags=["Two Factor Auth"])
app.include_router(lockout_router, prefix="/api/auth", tags=["User Lockout"])
app.include_router(rbac_router, prefix="/api/rbac", tags=["Role Based Access"])
app.include_router(shift_router, prefix="/api", tags=["Shift Management"])
app.include_router(reports_router, prefix="/api", tags=["Manager Reports"])

# --------------------------------------------------
# ROOT & HEALTH ENDPOINTS
# --------------------------------------------------
@app.get("/")
def root():
    """Root endpoint returning API information."""
    return {
        "message": "Welcome to Helping Hands API",
        "version": "1.0.0",
        "team": "TRM"
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# --------------------------------------------------
# MAIN ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # For production, use environment variables to configure the host
    host = os.getenv("API_HOST", "127.0.0.1")  # Default to localhost
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)

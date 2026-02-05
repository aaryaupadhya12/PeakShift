from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from backend.config import get_connection

router = APIRouter()


class LockoutCheck(BaseModel):
    username: str


def get_db():
    return get_connection()


@router.get("/check-lockout/{username}")
def check_user_lockout(username: str):
    """
    Check if user account is locked
    - Returns lockout status
    - Returns remaining lockout time if locked
    """
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user['locked_until']:
        locked_until = datetime.fromisoformat(user['locked_until'])
        if locked_until > datetime.now():
            remaining_time = (locked_until - datetime.now()).total_seconds()
            return {
                "locked": True,
                "locked_until": user['locked_until'],
                "remaining_seconds": int(remaining_time),
                "message": f"Account locked for {int(remaining_time/60)} more minutes"
            }

    return {
        "locked": False,
        "attempts": user['attempts'],
        "message": "Account is active"
    }


@router.post("/record-failed-attempt")
def record_failed_login_attempt(username: str):
    """
    Record failed login attempt
    - Increments attempt counter
    - Locks account after 3 failed attempts
    - Lockout duration: 15 minutes
    """
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_attempts = user['attempts'] + 1

    # Lock account after 3 failed attempts
    if new_attempts >= 3:
        locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
        conn.execute(
            "UPDATE users SET attempts=?, locked_until=? WHERE username=?",
            (new_attempts, locked_until, username)
        )
        conn.commit()

        return {
            "locked": True,
            "attempts": new_attempts,
            "locked_until": locked_until,
            "message": "Account locked for 15 minutes due to multiple failed attempts"
        }
    else:
        conn.execute(
            "UPDATE users SET attempts=? WHERE username=?",
            (new_attempts, username)
        )
        conn.commit()

        return {
            "locked": False,
            "attempts": new_attempts,
            "remaining_attempts": 3 - new_attempts,
            "message": f"Failed attempt recorded. {3 - new_attempts} attempts remaining"
        }


@router.post("/reset-attempts")
def reset_login_attempts(username: str):
    """
    Reset failed login attempts counter
    - Called after successful login
    - Clears lockout status
    """
    conn = get_db()

    conn.execute(
        "UPDATE users SET attempts=0, locked_until=NULL WHERE username=?",
        (username,)
    )
    conn.commit()

    return {
        "success": True,
        "message": "Login attempts reset successfully"
    }

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import secrets
from datetime import datetime, timedelta
from backend.config import get_connection

router = APIRouter()


class OTPRequest(BaseModel):
    username: str
    otp: str


def get_db():
    return get_connection()


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


@router.post("/generate-otp")
def generate_otp_for_admin(username: str):
    """
    Generate OTP for admin users
    - Creates a 6-digit OTP
    - Sets expiration time to 5 minutes
    """
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="OTP only required for admin users")

    # Generate OTP
    otp = generate_otp()
    otp_expires = (datetime.now() + timedelta(minutes=5)).isoformat()

    # Store OTP in database
    conn.execute(
        "UPDATE users SET otp=?, otp_expires=? WHERE username=?",
        (otp, otp_expires, username)
    )
    conn.commit()

    return {
        "requires_otp": True,
        "otp": otp,  # In production, send via SMS/Email instead of returning
        "expires_in": "5 minutes"
    }


@router.post("/verify-otp")
def verify_otp(req: OTPRequest):
    """
    Verify OTP for admin users
    - Validates OTP against stored value
    - Checks expiration time
    """
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (req.username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user['otp']:
        raise HTTPException(status_code=400, detail="No OTP generated")

    if user['otp'] != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if datetime.fromisoformat(user['otp_expires']) < datetime.now():
        raise HTTPException(status_code=400, detail="OTP expired")

    # Clear OTP after successful verification
    conn.execute(
        "UPDATE users SET otp=NULL, otp_expires=NULL WHERE username=?",
        (req.username,)
    )
    conn.commit()

    return {
        "verified": True,
        "message": "OTP verified successfully"
    }

"""User login endpoint and rate limiting helpers."""

import hashlib
import time

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from backend.config import get_connection

# Simple in-memory rate limiter (shared)
RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10    # max requests per window

def rate_limiter(request: Request):
    ip = request.client.host
    now = time.time()
    window = int(now // RATE_LIMIT_WINDOW)
    key = f"{ip}:{window}"
    count = RATE_LIMIT.get(key, 0)
    if count >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests, slow down.")
    RATE_LIMIT[key] = count + 1

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


def get_db():
    return get_connection()


@router.post("/login")
def user_login(req: LoginRequest, _: None = Depends(rate_limiter)):
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (req.username,)
    ).fetchone()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    hashed_password = hashlib.sha256(req.password.encode()).hexdigest()
    if hashed_password != user['password']:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Return credits if present (for reward system UI)
    result = {
        "username": req.username,
        "role": user['role'],
        "message": "Login successful"
    }
    if 'credits' in user.keys():
        result["credits"] = user["credits"]
    return result
"""Shift management endpoints and helper functions.

Provides routes for creating, publishing, signing up and managing shifts.
"""

import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from backend.config import get_connection
from backend import email_service
import threading

# Simple in-memory rate limiter
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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

router = APIRouter()


class ShiftCreate(BaseModel):
    """Request model for creating a new shift."""
    title: str
    date: str
    start_time: str
    end_time: str
    spots: int
    location: str = "Default Location"  # Optional with default value


class VolunteerSignup(BaseModel):
    """Request model for volunteer signup to a shift."""
    shift_id: int
    username: str


class ShiftApproval(BaseModel):
    """Request model for approving/rejecting volunteer commitment."""
    volunteer_commitment_id: int
    approved: bool


class ShiftUpdate(BaseModel):
    """Request model for updating shift status."""
    status: str


def get_db():
    """Get database connection with row factory."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/shifts")
def create_shift(shift: ShiftCreate, created_by: str):
    """Manager creates shift (draft status)"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Validate manager or admin role
        user_role = cursor.execute(
            "SELECT role FROM users WHERE username = ?",
            (created_by,),
        ).fetchone()

        if not user_role or user_role[0] not in ("manager", "admin"):
            raise HTTPException(
                status_code=403, detail="Only managers and admins can create shifts"
            )

        # Create the shift
        cursor.execute(
            """INSERT INTO shifts
            (title, date, start_time, end_time, spots, location, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                shift.title,
                shift.date,
                shift.start_time,
                shift.end_time,
                shift.spots,
                shift.location,
                "draft",
                created_by,
            ),
        )
        shift_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": shift_id,
            "status": "draft",
            "message": "Shift created, awaiting admin validation",
        }
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e


@router.post("/shifts/{shift_id}/validate")
def validate_shift(shift_id: int, validated_by: str):
    """Admin validates shift"""
    conn = get_db()
    conn.execute("UPDATE shifts SET status=? WHERE id=?", ("validated", shift_id))
    conn.commit()
    return {"id": shift_id, "status": "validated", "validated_by": validated_by}


@router.post("/shifts/{shift_id}/publish")
def publish_shift(shift_id: int, published_by: str):
    """Manager publishes validated shift"""
    conn = get_db()
    conn.execute("UPDATE shifts SET status=? WHERE id=?", ("published", shift_id))
    conn.commit()
    # Fetch shift details to include in notifications
    try:
        cursor = conn.cursor()
        shift_row = cursor.execute("SELECT * FROM shifts WHERE id=?", (shift_id,)).fetchone()
        if shift_row:
            shift = dict(shift_row)
            # Add a role field if not present for email body clarity
            shift.setdefault('role', 'Volunteer')

            # Send notifications in a background thread to avoid blocking the response
            def _notify():
                try:
                    email_service.send_new_shift_notification(shift)
                except Exception as e:
                    print(f"Error sending shift notification: {e}")

            t = threading.Thread(target=_notify, daemon=True)
            t.start()
    except Exception as e:
        print(f"Error preparing shift notification: {e}")
    return {"id": shift_id, "status": "published", "published_by": published_by}


@router.delete("/shifts/{shift_id}")
def cancel_shift(shift_id: int, cancelled_by: str, role: str):
    """Manager/Admin cancels shift"""
    if role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admin/manager can cancel shifts")
    conn = get_db()
    conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
    conn.commit()
    return {"message": "Shift cancelled"}


def check_shift_overlap(conn, username: str, new_shift_id: int) -> bool:
    """Check if volunteer has any overlapping shifts"""
    try:
        shift = conn.execute(
            "SELECT date, start_time, end_time FROM shifts WHERE id=?",
            (new_shift_id,)
        ).fetchone()

        if not shift:
            return False

        existing_shifts = conn.execute("""
            SELECT s.date, s.start_time, s.end_time
            FROM shifts s
            JOIN volunteer_commitments vc ON s.id = vc.shift_id
            WHERE vc.username = ? AND vc.status IN ('pending', 'approved')
        """, (username,)).fetchall()

        # Parse new shift times
        try:
            new_start = datetime.strptime(
                f"{shift['date']} {shift['start_time']}", "%Y-%m-%d %H:%M"
            )
            new_end = datetime.strptime(
                f"{shift['date']} {shift['end_time']}", "%Y-%m-%d %H:%M"
            )
        except (ValueError, TypeError) as e:
            print(f"Error parsing new shift times: {e}")
            return False

        for existing in existing_shifts:
            try:
                start = datetime.strptime(
                    f"{existing['date']} {existing['start_time']}",
                    "%Y-%m-%d %H:%M"
                )
                end = datetime.strptime(
                    f"{existing['date']} {existing['end_time']}",
                    "%Y-%m-%d %H:%M"
                )

                if (start <= new_end and end >= new_start):
                    return True
            except (ValueError, TypeError) as e:
                print(f"Error parsing existing shift times: {e}")
                continue

        return False
    except Exception as e:
        print(f"Error in check_shift_overlap: {e}")
        return False


def get_alternative_shifts(conn, shift_id: int) -> List[dict]:
    """Get alternative shifts on the same day"""
    try:
        shift = conn.execute(
            "SELECT date FROM shifts WHERE id=?",
            (shift_id,)
        ).fetchone()

        if not shift:
            return []

        return [dict(s) for s in conn.execute(
            "SELECT * FROM shifts WHERE date=? AND id!=? AND status='published' AND spots > 0",
            (shift['date'], shift_id)
        ).fetchall()]
    except Exception as e:
        print(f"Error getting alternative shifts: {e}")
        return []


@router.post("/shifts/{shift_id}/volunteer")
async def volunteer_for_shift(shift_id: int, username: str, _: None = Depends(rate_limiter)):
    """Volunteer signs up for a shift"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # First validate that the user exists and is a volunteer
        user = cursor.execute(
            "SELECT role FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        if user['role'] != 'volunteer':
            raise HTTPException(status_code=403, detail="Only volunteers can sign up for shifts")

        # Check if shift exists and has spots
        shift = cursor.execute(
            "SELECT * FROM shifts WHERE id=? AND status='published'",
            (shift_id,)
        ).fetchone()

        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found or not published")

        if shift['spots'] <= 0:
            raise HTTPException(status_code=400, detail="No spots available")

        # Check if already signed up or previously rejected
        existing_commitment = cursor.execute("""
            SELECT id, status FROM volunteer_commitments
            WHERE username = ? AND shift_id = ?
        """, (username, shift_id)).fetchone()

        if existing_commitment:
            if existing_commitment['status'] == 'rejected':
                raise HTTPException(
                    status_code=403,
                    detail="You were previously rejected for this shift and cannot sign up again"
                )
            if existing_commitment['status'] in ('pending', 'approved'):
                raise HTTPException(
                    status_code=400,
                    detail="Already signed up for this shift"
                )

        # Check for overlapping shifts
        try:
            if check_shift_overlap(conn, username, shift_id):
                alternative_shifts = get_alternative_shifts(conn, shift_id)
                return {
                    "status": "overlap",
                    "message": "You have an overlapping shift",
                    "alternative_shifts": alternative_shifts
                }
        except Exception as overlap_error:
            print(f"Error checking overlap: {overlap_error}")
            # Continue with signup even if overlap check fails

        # Create volunteer commitment
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO volunteer_commitments
            (username, shift_id, volunteered_at, status)
            VALUES (?, ?, ?, 'pending')
        """, (username, shift_id, now))

        commitment_id = cursor.lastrowid
        conn.commit()

        return {
            "status": "pending",
            "message": "Volunteer request submitted, awaiting approval",
            "commitment_id": commitment_id
        }

    except HTTPException:
        raise
    except sqlite3.Error as e:
        print(f"Database error in volunteer_for_shift: {e}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e
    except Exception as e:
        print(f"Unexpected error in volunteer_for_shift: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e


class ApprovalRequest(BaseModel):
    volunteer_commitment_id: int
    approved: bool
    manager_username: str

@router.post("/volunteer-commitments/{commitment_id}/approve")
async def approve_volunteer(commitment_id: int, approval: ShiftApproval, manager_username: str):
    """Manager approves or rejects volunteer commitment"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Validate manager role
        user_role = cursor.execute(
            "SELECT role FROM users WHERE username = ?",
            (manager_username,),
        ).fetchone()

        if not user_role or user_role[0] != "manager":
            raise HTTPException(status_code=403, detail="Only managers can approve volunteers")

        commitment = cursor.execute("""
            SELECT vc.*, s.spots, s.id as shift_id
            FROM volunteer_commitments vc
            JOIN shifts s ON vc.shift_id = s.id
            WHERE vc.id = ?
        """, (commitment_id,)).fetchone()

        if not commitment:
            raise HTTPException(status_code=404, detail="Volunteer commitment not found")

        if commitment['status'] != 'pending':
            raise HTTPException(status_code=400, detail="Commitment already processed")

        now = datetime.now()

        if approval.approved:
            # Check if spots are still available
            shift = cursor.execute(
                "SELECT spots FROM shifts WHERE id = ?",
                (commitment['shift_id'],)
            ).fetchone()

            if shift['spots'] <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="No spots available"
                )

            # Update commitment status and set cancellation window
            cancel_until = now + timedelta(hours=12)
            cursor.execute("""
                UPDATE volunteer_commitments
                SET status = 'approved',
                    approved_at = ?,
                    approved_by = ?,
                    can_cancel_until = ?
                WHERE id = ?
            """, (now.isoformat(), manager_username, cancel_until.isoformat(), commitment_id))

            # Decrement available spots
            cursor.execute(
                "UPDATE shifts SET spots = spots - 1 WHERE id = ?",
                (commitment['shift_id'],)
            )

            # Reward: increment volunteer credits so managers can preferentially accept
            try:
                # Ensure the users table has a credits column (safe for legacy DBs)
                cols = [row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
                if 'credits' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 0")

                cursor.execute(
                    "UPDATE users SET credits = COALESCE(credits, 0) + 1 WHERE username = ?",
                    (commitment['username'],)
                )
            except sqlite3.Error:
                # Non-fatal: if we can't add/increment credits, continue without blocking approval
                pass

        else:
            cursor.execute(
                "UPDATE volunteer_commitments SET status = 'rejected' WHERE id = ?",
                (commitment_id,)
            )

        conn.commit()

        return {
            "status": "approved" if approval.approved else "rejected",
            "message": f"Volunteer commitment {'approved' if approval.approved else 'rejected'}",
            "can_cancel_until": cancel_until.isoformat() if approval.approved else None
        }

    except sqlite3.Error as e:
        print(f"Database error in approve_volunteer: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e
    except Exception as e:
        print(f"Unexpected error in approve_volunteer: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e


@router.post("/volunteer-commitments/{commitment_id}/cancel")
def cancel_commitment(commitment_id: int, username: str):
    """Volunteer cancels their commitment within the allowed window"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        commitment = cursor.execute("""
            SELECT * FROM volunteer_commitments
            WHERE id = ? AND username = ? AND status = 'approved'
        """, (commitment_id, username)).fetchone()

        if not commitment:
            raise HTTPException(
                status_code=404,
                detail="Commitment not found or not approved"
            )

        now = datetime.now()
        can_cancel_until = datetime.fromisoformat(commitment['can_cancel_until'])

        if now > can_cancel_until:
            raise HTTPException(
                status_code=400,
                detail="Cancellation window has expired"
            )

        # Update commitment status
        cursor.execute(
            "UPDATE volunteer_commitments SET status = 'cancelled' WHERE id = ?",
            (commitment_id,)
        )

        # Increment available spots
        cursor.execute(
            "UPDATE shifts SET spots = spots + 1 WHERE id = ?",
            (commitment['shift_id'],)
        )

        conn.commit()

        return {
            "status": "cancelled",
            "message": "Volunteer commitment cancelled successfully"
        }

    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e


@router.get("/volunteer-commitments")
async def get_volunteer_commitments(username: str):
    """Get all commitments for a volunteer"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        commitments = cursor.execute("""
            SELECT vc.*, s.title as shift_title, s.date, s.start_time, s.end_time
            FROM volunteer_commitments vc
            JOIN shifts s ON vc.shift_id = s.id
            WHERE vc.username = ?
            ORDER BY s.date, s.start_time
        """, (username,)).fetchall()

        return [dict(commitment) for commitment in commitments]

    except sqlite3.Error as e:
        print(f"Database error in get_volunteer_commitments: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e


@router.get("/shifts")
def get_shifts(status: Optional[str] = None, user_role: Optional[str] = None):
    """Get all shifts (optionally filter by status and user role)"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Build the WHERE clause based on role and status
        where_clauses = []
        params = []

        if user_role == 'volunteer':
            where_clauses.append("s.status = 'published'")
        elif user_role in ['admin', 'manager']:
            # Admin and manager can see all statuses
            if status:
                where_clauses.append("s.status = ?")
                params.append(status)
        else:
            # If no role specified, assume volunteer for safety
            where_clauses.append("s.status = 'published'")

        base_query = """
            SELECT s.*,
                (SELECT COUNT(*) FROM volunteer_commitments vc
                 WHERE vc.shift_id = s.id AND vc.status = 'pending') as pending_count,
                (SELECT json_group_array(json_object(
                    'username', vc.username,
                    'commitment_id', vc.id
                ))
                 FROM volunteer_commitments vc
                 WHERE vc.shift_id = s.id AND vc.status = 'pending'
                ) as pending_volunteers
            FROM shifts s
        """
        query = base_query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY s.date, s.start_time"

        shifts = cursor.execute(query, params).fetchall()

        result = []
        for shift in shifts:
            shift_dict = dict(shift)
            if shift_dict['pending_volunteers'] == '[null]':
                shift_dict['pending_volunteers'] = []
            else:
                try:
                    shift_dict['pending_volunteers'] = json.loads(shift_dict['pending_volunteers'])
                except json.JSONDecodeError:
                    shift_dict['pending_volunteers'] = []
                except Exception:
                    # Unexpected parsing error — return empty list for safety
                    shift_dict['pending_volunteers'] = []
            result.append(shift_dict)

        return result

    except sqlite3.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error: {str(e)}"
        ) from e

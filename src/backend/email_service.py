"""Simple email notification service using SendGrid.

This module exposes a send_new_shift_notification function which accepts
shift details and sends an email to all eligible staff (managers and admins).
Environment variables:
 - SENDGRID_API_KEY: API key for SendGrid
 - FROM_EMAIL: sender email address
 - FRONTEND_URL: base URL for frontend to build volunteer links (e.g., http://localhost:3000)
"""
import os
import json
from typing import Dict, List

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except Exception:
    # When sendgrid isn't installed, we still want the module to import for tests.
    SendGridAPIClient = None
    Mail = None

from backend.config import get_connection


def _get_staff_emails() -> List[str]:
    """Return list of emails for users with role manager or admin.

    This project stores only usernames in the users table. For demo purposes
    we assume username is an email address. In a real system, add an email
    column to users table and use that.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        rows = cursor.execute("SELECT username FROM users WHERE role IN ('manager','admin')").fetchall()
        return [r[0] for r in rows if r and r[0]]
    finally:
        conn.close()


def _build_email_content(shift: Dict, frontend_url: str) -> Dict[str, str]:
    subject = f"New shift posted: {shift.get('title')} on {shift.get('date')}"
    volunteer_link = f"{frontend_url.rstrip('/')}/?openShift={shift.get('id')}"  # simple deep-link

    body = f"A new shift has been posted:\n\nTitle: {shift.get('title')}\nDate: {shift.get('date')}\nTime: {shift.get('start_time')} - {shift.get('end_time')}\nRole: {shift.get('role', 'N/A')}\nLocation: {shift.get('location')}\nSpots: {shift.get('spots')}\n\nVolunteer here: {volunteer_link}\n\n"

    # Also include JSON metadata for debugging
    body += "\n--\nRaw details:\n" + json.dumps(shift, default=str)

    return {"subject": subject, "body": body, "link": volunteer_link}


def send_new_shift_notification(shift: Dict) -> bool:
    """Send notification emails to all eligible staff.

    Returns True on success, False on failure. Non-fatal errors are caught and
    logged to stdout.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "no-reply@example.com")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    recipients = _get_staff_emails()
    if not recipients:
        print("No staff recipients found for shift notification")
        return False

    content = _build_email_content(shift, frontend_url)

    if not SendGridAPIClient or not Mail or not api_key:
        # Fallback: print to stdout (useful in tests or local dev without SendGrid)
        print("[EmailService] Fallback - would send email to:", recipients)
        print("Subject:", content['subject'])
        print(content['body'])
        return False

    message = Mail(
        from_email=from_email,
        to_emails=recipients,
        subject=content['subject'],
        plain_text_content=content['body']
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"[EmailService] Sent shift notification, status_code={response.status_code}")
        return 200 <= response.status_code < 300
    except Exception as e:
        print(f"[EmailService] Error sending email: {e}")
        return False

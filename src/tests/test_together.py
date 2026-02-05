"""
Unified Backend Test Suite (CI/CD Safe)
Covers Authentication, RBAC, Lockout, OTP, and Shift Management
"""

import os
import sys
import sqlite3
import hashlib
import tempfile
import pytest
from fastapi.testclient import TestClient

# --- Ensure project `src` is on sys.path so package imports work ---
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, src_path)

# --- Use shared in-memory DB for CI/testing ---
# Setting TEST_MODE instructs the application to use a shared in-memory SQLite URI
os.environ["TEST_MODE"] = "1"
TEST_DB_PATH = "file:shared_mem_db?mode=memory&cache=shared"
os.environ["TEST_DB_PATH"] = TEST_DB_PATH


# --- Initialize DB (replicates init_db.py schema) ---
def create_test_db(path: str):
    """Create or reset a SQLite database for tests.

    Supports both file-backed DBs and the shared in-memory URI.
    """
    # For file: URIs (shared in-memory) we must connect with uri=True and
    # cannot remove the file — instead drop existing tables to reset state.
    if path.startswith("file:"):
        conn = sqlite3.connect(path, uri=True)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS volunteer_commitments")
        cursor.execute("DROP TABLE IF EXISTS shifts")
        cursor.execute("DROP TABLE IF EXISTS users")
    else:
        if os.path.exists(path):
            os.remove(path)
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

    # Users table
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

    # Shifts table
    cursor.execute("""
        CREATE TABLE shifts (
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

    # Volunteer commitments
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

    # Seed sample users
    sample_users = [
        ('admin', 'admin123', 'admin'),
        ('manager', 'manager123', 'manager'),
        ('volunteer', 'volunteer123', 'volunteer'),
        ('testuser', 'testpass123', 'volunteer'),
        ('locktest_user', 'test123', 'volunteer'),
    ]

    for username, password, role in sample_users:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, 0, NULL, NULL, NULL, 0)",
            (username, hashed, role),
        )

    conn.commit()
    conn.close()


# --- Create DB before importing app ---
create_test_db(TEST_DB_PATH)

# Keep a persistent connection open for the shared in-memory DB so the
# database does not disappear when the setup connection closes. SQLite
# in-memory databases live only as long as a connection remains open.
PERSISTENT_CONN = None
if TEST_DB_PATH.startswith("file:"):
    PERSISTENT_CONN = sqlite3.connect(TEST_DB_PATH, uri=True, check_same_thread=False)

from backend.main import app  # Must import AFTER DB is ready
client = TestClient(app)


# --- Fixtures ---
@pytest.fixture(scope='function', autouse=True)
def reset_db():
    """Reinitialize DB before each test (isolated + repeatable)"""
    create_test_db(TEST_DB_PATH)
    yield


# ==========================================================
# AUTHENTICATION TESTS
# ==========================================================
class TestUserLogin:
    def test_login_success_volunteer(self):
        r = client.post("/api/auth/login", json={
            "username": "volunteer",
            "password": "volunteer123"
        })
        assert r.status_code == 200
        d = r.json()
        assert d["username"] == "volunteer"
        assert d["role"] == "volunteer"
        assert d["message"] == "Login successful"

    def test_login_success_admin(self):
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_login_invalid_password(self):
        r = client.post("/api/auth/login", json={
            "username": "volunteer",
            "password": "wrongpassword"
        })
        assert r.status_code == 400
        assert "Invalid credentials" in r.json()["detail"]

    def test_login_nonexistent_user(self):
        r = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "password"
        })
        assert r.status_code == 400


# ==========================================================
# TWO-FACTOR AUTH (OTP)
# ==========================================================
class TestTwoFactorAuth:
    def test_generate_otp_for_admin(self):
        r = client.post("/api/auth/generate-otp?username=admin")
        assert r.status_code == 200
        d = r.json()
        assert "otp" in d
        assert len(d["otp"]) == 6
        assert d["requires_otp"] is True

    def test_generate_otp_non_admin_fails(self):
        r = client.post("/api/auth/generate-otp?username=volunteer")
        assert r.status_code == 403
        assert "admin users" in r.json()["detail"]

    def test_verify_otp_invalid(self):
        client.post("/api/auth/generate-otp?username=admin")
        r = client.post("/api/auth/verify-otp", json={
            "username": "admin",
            "otp": "000000"
        })
        assert r.status_code == 400


# ==========================================================
# ACCOUNT LOCKOUT
# ==========================================================
class TestUserLockout:
    def test_check_lockout_active_user(self):
        r = client.get("/api/auth/check-lockout/volunteer")
        assert r.status_code == 200
        assert "locked" in r.json()

    def test_record_failed_attempt(self):
        r = client.post("/api/auth/record-failed-attempt?username=testuser")
        assert r.status_code == 200
        d = r.json()
        assert d["attempts"] >= 1

    def test_reset_attempts(self):
        r = client.post("/api/auth/reset-attempts?username=testuser")
        assert r.status_code == 200
        assert r.json()["success"] is True


# ==========================================================
# ROLE-BASED ACCESS CONTROL
# ==========================================================
class TestRoleBasedAccess:
    def test_get_admin_permissions(self):
        r = client.get("/api/rbac/roles/admin/permissions")
        assert r.status_code == 200
        d = r.json()
        assert "manage_users" in d["permissions"]

    def test_get_volunteer_permissions(self):
        r = client.get("/api/rbac/roles/volunteer/permissions")
        assert r.status_code == 200
        d = r.json()
        assert "volunteer_for_shift" in d["permissions"]

    def test_check_user_permission_allowed(self):
        r = client.get("/api/rbac/check-permission?username=admin&action=manage_users")
        assert r.status_code == 200
        assert r.json()["has_permission"] is True

    def test_check_user_permission_denied(self):
        r = client.get("/api/rbac/check-permission?username=volunteer&action=manage_users")
        assert r.status_code == 200
        assert r.json()["has_permission"] is False

    def test_validate_action_success(self):
        r = client.post("/api/rbac/validate-action?username=admin&role=admin&action=manage_users")
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_validate_action_failure(self):
        r = client.post("/api/rbac/validate-action?username=volunteer&role=volunteer&action=manage_users")
        assert r.status_code == 403


# ==========================================================
# SHIFT MANAGEMENT
# ==========================================================
class TestShiftManagement:
    """Shift creation, validation, publishing, and cancellation"""

    def test_create_shift(self):
        r = client.post("/api/shifts?created_by=manager", json={
            "title": "Food Drive",
            "date": "2025-12-01",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 10
        })
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_validate_shift(self):
        c = client.post("/api/shifts?created_by=manager", json={
            "title": "Test Shift",
            "date": "2025-12-02",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        shift_id = c.json()["id"]

        r = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        assert r.status_code == 200
        assert r.json()["status"] == "validated"

    def test_publish_shift(self):
        c = client.post("/api/shifts?created_by=manager", json={
            "title": "Publish Shift",
            "date": "2025-12-03",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        shift_id = c.json()["id"]

        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        r = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        assert r.status_code == 200
        assert r.json()["status"] == "published"

    def test_cancel_shift_manager(self):
        c = client.post("/api/shifts?created_by=manager", json={
            "title": "Cancel Shift",
            "date": "2025-12-04",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        shift_id = c.json()["id"]

        r = client.delete(f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager")
        assert r.status_code == 200
        assert "cancelled" in r.json()["message"].lower()

    def test_get_all_shifts(self):
        r = client.get("/api/shifts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unauthorized_shift_creation(self):
        r = client.post("/api/shifts?created_by=volunteer", json={
            "title": "Unauthorized Shift",
            "date": "2025-12-05",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        assert r.status_code == 403
        assert "only managers" in r.json()["detail"].lower()

    def test_unauthorized_shift_cancellation(self):
        c = client.post("/api/shifts?created_by=manager", json={
            "title": "Cancel Attempt Shift",
            "date": "2025-12-06",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        shift_id = c.json()["id"]

        r = client.delete(f"/api/shifts/{shift_id}?cancelled_by=volunteer&role=volunteer")
        assert r.status_code == 403
        assert "only admin/manager" in r.json()["detail"].lower()

    def test_shift_workflow(self):
        create = client.post("/api/shifts?created_by=manager", json={
            "title": "Workflow Shift",
            "date": "2025-12-07",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 5
        })
        shift_id = create.json()["id"]

        validate = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        assert validate.status_code == 200

        publish = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        assert publish.status_code == 200
        assert publish.json()["status"] == "published"

        get_all = client.get("/api/shifts")
        assert any(s["id"] == shift_id and s["status"] == "published" for s in get_all.json())

    def test_volunteer_signup(self):
        # Create and publish a shift
        create = client.post("/api/shifts?created_by=manager", json={
            "title": "Volunteer Test Shift",
            "date": "2025-12-08",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 2
        })
        shift_id = create.json()["id"]
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")

        # Volunteer signs up
        signup = client.post(f"/api/shifts/{shift_id}/volunteer?username=volunteer")
        assert signup.status_code == 200
        assert signup.json()["status"] == "pending"
        commitment_id = signup.json()["commitment_id"]

        # Manager approves
        approve = client.post(f"/api/volunteer-commitments/{commitment_id}/approve?manager_username=manager", json={
            "volunteer_commitment_id": commitment_id,
            "approved": True
        })
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
        assert "can_cancel_until" in approve.json()
        
        # Verify volunteer received a credit
        # Connect directly to test DB and ensure credits increased for 'volunteer'
        conn = sqlite3.connect(TEST_DB_PATH, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT credits FROM users WHERE username = ?", ('volunteer',))
        credits_row = cur.fetchone()
        conn.close()
        assert credits_row is not None
        assert credits_row[0] >= 1

    def test_overlapping_shifts(self):
        # Create and publish two shifts with overlapping times
        shift1 = client.post("/api/shifts?created_by=manager", json={
            "title": "Morning Shift",
            "date": "2025-12-09",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 2
        })
        shift1_id = shift1.json()["id"]
        client.post(f"/api/shifts/{shift1_id}/validate?validated_by=admin")
        client.post(f"/api/shifts/{shift1_id}/publish?published_by=manager")

        shift2 = client.post("/api/shifts?created_by=manager", json={
            "title": "Overlapping Shift",
            "date": "2025-12-09",
            "start_time": "12:00",
            "end_time": "16:00",
            "spots": 2
        })
        shift2_id = shift2.json()["id"]
        client.post(f"/api/shifts/{shift2_id}/validate?validated_by=admin")
        client.post(f"/api/shifts/{shift2_id}/publish?published_by=manager")

        # Sign up for first shift
        signup1 = client.post(f"/api/shifts/{shift1_id}/volunteer?username=volunteer")
        commitment_id = signup1.json()["commitment_id"]
        client.post(f"/api/volunteer-commitments/{commitment_id}/approve?manager_username=manager", json={
            "volunteer_commitment_id": commitment_id,
            "approved": True
        })

        # Try to sign up for overlapping shift
        signup2 = client.post(f"/api/shifts/{shift2_id}/volunteer?username=volunteer")
        assert signup2.json()["status"] == "overlap"
        assert "alternative_shifts" in signup2.json()

    def test_cancellation_window(self):
        # Create and publish a shift
        shift = client.post("/api/shifts?created_by=manager", json={
            "title": "Cancellation Test Shift",
            "date": "2025-12-10",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 2
        })
        shift_id = shift.json()["id"]
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")

        # Volunteer signs up and gets approved
        signup = client.post(f"/api/shifts/{shift_id}/volunteer?username=volunteer")
        commitment_id = signup.json()["commitment_id"]
        
        approve = client.post(f"/api/volunteer-commitments/{commitment_id}/approve?manager_username=manager", json={
            "volunteer_commitment_id": commitment_id,
            "approved": True
        })
        assert approve.status_code == 200

        # Cancel commitment
        cancel = client.post(f"/api/volunteer-commitments/{commitment_id}/cancel?username=volunteer")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        # Verify spot is available again
        shifts = client.get("/api/shifts")
        shift_data = next(s for s in shifts.json() if s["id"] == shift_id)
        assert shift_data["spots"] == 2  # Back to original count


# ==========================================================
# MANAGER COVERAGE REPORT TESTS
# ==========================================================
class TestManagerCoverageReport:
    """Tests for manager coverage reporting functionality."""
    
    def test_filter_shifts_by_location(self):
        """Test filtering shifts by location using the coverage report module."""
        from backend import manager_coverage_report as mcr
        
        shifts = [
            {"id": "s1", "date": "2025-11-01", "location": "Store A", "required_staff": 1, "assigned_staff": ["u1"]},
            {"id": "s2", "date": "2025-11-02", "location": "Store B", "required_staff": 1, "assigned_staff": ["u2"]},
            {"id": "s3", "date": "2025-11-03", "location": "Store A", "required_staff": 1, "assigned_staff": []},
        ]
        
        filtered = mcr.filter_shifts(shifts, location="Store A")
        assert len(filtered) == 2
        assert all(s["location"] == "Store A" for s in filtered)
    
    def test_shifts_fill_status(self):
        """Test shift fill status annotation."""
        from backend import manager_coverage_report as mcr
        
        shifts = [
            {"id": "s1", "date": "2025-11-01", "location": "Store A", "required_staff": 2, "assigned_staff": ["u1", "u2"]},
            {"id": "s2", "date": "2025-11-02", "location": "Store A", "required_staff": 1, "assigned_staff": []},
        ]
        
        annotated = mcr.shifts_with_fill_status(shifts)
        
        # s1 should be filled
        s1 = next(s for s in annotated if s["id"] == "s1")
        assert s1["filled"] is True
        assert s1["assigned_count"] == 2
        
        # s2 should not be filled
        s2 = next(s for s in annotated if s["id"] == "s2")
        assert s2["filled"] is False
        assert s2["assigned_count"] == 0
    
    def test_participation_rate(self):
        """Test participation rate calculation."""
        from backend import manager_coverage_report as mcr
        
        shifts = [
            {"id": "s1", "assigned_staff": ["u1", "u2"]},
            {"id": "s2", "assigned_staff": ["u1"]},
            {"id": "s3", "assigned_staff": ["u2"]},
        ]
        
        participation = mcr.participation_rate_by_staff(shifts)
        
        # u1 participated in 2 out of 3 shifts
        assert participation["u1"]["assigned"] == 2
        assert abs(participation["u1"]["rate"] - (2.0 / 3.0)) < 1e-9
        
        # u2 participated in 2 out of 3 shifts
        assert participation["u2"]["assigned"] == 2
        assert abs(participation["u2"]["rate"] - (2.0 / 3.0)) < 1e-9
    
    def test_generate_report(self):
        """Test complete report generation."""
        from backend import manager_coverage_report as mcr
        
        shifts = [
            {"id": "s1", "date": "2025-11-01", "location": "Store A", "required_staff": 2, "assigned_staff": ["u1", "u2"]},
            {"id": "s2", "date": "2025-11-02", "location": "Store A", "required_staff": 1, "assigned_staff": ["u1"]},
        ]
        
        report = mcr.generate_report(shifts, location="Store A")
        
        assert "shifts" in report
        assert "participation" in report
        assert "total_shifts" in report
        assert report["total_shifts"] == 2
    
    def test_report_to_csv(self):
        """Test CSV export functionality."""
        from backend import manager_coverage_report as mcr
        
        shifts = [
            {"id": "s1", "date": "2025-11-01", "location": "Store A", "required_staff": 1, "assigned_staff": ["u1"]},
        ]
        
        report = mcr.generate_report(shifts)
        csv_text = mcr.report_to_csv(report)
        
        # Verify CSV headers
        assert "id,date,location,required_staff,assigned_count,filled" in csv_text
        assert "staff_id,assigned,rate" in csv_text
        
        # Verify data is present
        assert "s1" in csv_text
        assert "u1" in csv_text
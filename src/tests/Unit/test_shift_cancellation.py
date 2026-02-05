"""
Test Suite: Shift Cancellation
Tests manager/admin ability to cancel/delete shifts
"""

import os
import sys
import sqlite3
import hashlib
import pytest
from fastapi.testclient import TestClient

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, src_path)

# Set test mode - MUST be set BEFORE importing app
os.environ["TEST_MODE"] = "1"
# Use unique in-memory database name for this test file
TEST_DB_PATH = "file:memdb_shift_cancellation?mode=memory&cache=shared"
os.environ["TEST_DB_PATH"] = TEST_DB_PATH


def create_test_db():
    """Initialize test database in memory only"""
    conn = sqlite3.connect(TEST_DB_PATH, uri=True, check_same_thread=False)
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS volunteer_commitments")
    cursor.execute("DROP TABLE IF EXISTS shifts")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'manager', 'volunteer')),
            attempts INTEGER DEFAULT 0,
            locked_until TEXT,
            otp TEXT,
            otp_expires TEXT
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
            created_by TEXT
        )
    """)
    
    # Create volunteer commitments table
    cursor.execute("""
        CREATE TABLE volunteer_commitments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            shift_id INTEGER,
            volunteered_at TEXT
        )
    """)
    
    # Insert test users
    users = [
        ('admin', 'admin123', 'admin'),
        ('manager', 'manager123', 'manager'),
        ('volunteer', 'volunteer123', 'volunteer'),
    ]
    
    for username, password, role in users:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users VALUES (?, ?, ?, 0, NULL, NULL, NULL)",
            (username, hashed, role)
        )
    
    conn.commit()
    conn.close()


# Create DB and keep persistent connection
create_test_db()
PERSISTENT_CONN = sqlite3.connect(TEST_DB_PATH, uri=True, check_same_thread=False)

from backend.main import app
client = TestClient(app)


@pytest.fixture(scope='function', autouse=True)
def reset_db():
    """Reset database before each test"""
    create_test_db()
    yield


def create_shift(title, date, start_time, end_time, spots):
    """Helper: Create a draft shift"""
    response = client.post("/api/shifts?created_by=manager", json={
        "title": title,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "spots": spots
    })
    return response.json()["id"]


class TestShiftCancellation:
    """Test shift cancellation/deletion functionality"""
    
    def test_manager_cancels_shift(self):
        """Manager should be able to cancel shift"""
        shift_id = create_shift(
            "Cancellable Shift", "2025-11-15", "09:00", "13:00", 5
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
        assert "cancelled" in cancel_response.json()["message"].lower()
    
    def test_admin_cancels_shift(self):
        """Admin should be able to cancel shift"""
        shift_id = create_shift(
            "Admin Cancel Test", "2025-11-16", "10:00", "14:00", 3
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
        assert "cancelled" in cancel_response.json()["message"].lower()
    
    def test_volunteer_cannot_cancel_shift(self):
        """Volunteer should not be able to cancel shift"""
        shift_id = create_shift(
            "Protected Shift", "2025-11-17", "11:00", "15:00", 4
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=volunteer&role=volunteer"
        )
        
        assert cancel_response.status_code == 403
        assert "only admin/manager" in cancel_response.json()["detail"].lower()
    
    def test_cancelled_shift_removed_from_list(self):
        """Cancelled shift should not appear in shift list"""
        shift_id = create_shift(
            "Disappearing Shift", "2025-11-18", "09:00", "12:00", 5
        )
        
        # Verify shift exists
        shifts_before = client.get("/api/shifts").json()
        assert any(s["id"] == shift_id for s in shifts_before)
        
        # Cancel shift
        client.delete(f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager")
        
        # Verify shift no longer exists
        shifts_after = client.get("/api/shifts").json()
        assert not any(s["id"] == shift_id for s in shifts_after)
    
    def test_cancel_draft_shift(self):
        """Should be able to cancel shift in draft status"""
        shift_id = create_shift(
            "Draft Cancel", "2025-11-19", "10:00", "14:00", 3
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_validated_shift(self):
        """Should be able to cancel validated shift"""
        shift_id = create_shift(
            "Validated Cancel", "2025-11-20", "11:00", "15:00", 4
        )
        
        # Validate shift first
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Cancel validated shift
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_published_shift(self):
        """Should be able to cancel published shift"""
        shift_id = create_shift(
            "Published Cancel", "2025-11-21", "09:00", "13:00", 5
        )
        
        # Validate and publish
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        # Cancel published shift
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_multiple_shifts(self):
        """Should be able to cancel multiple shifts"""
        shift1 = create_shift("Shift 1", "2025-11-22", "09:00", "12:00", 3)
        shift2 = create_shift("Shift 2", "2025-11-23", "13:00", "16:00", 4)
        
        response1 = client.delete(
            f"/api/shifts/{shift1}?cancelled_by=manager&role=manager"
        )
        response2 = client.delete(
            f"/api/shifts/{shift2}?cancelled_by=manager&role=manager"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both removed
        shifts = client.get("/api/shifts").json()
        assert not any(s["id"] == shift1 for s in shifts)
        assert not any(s["id"] == shift2 for s in shifts)
    
    def test_cancel_shift_with_many_spots(self):
        """Should cancel shift with large number of spots"""
        shift_id = create_shift(
            "Large Event", "2025-11-24", "08:00", "18:00", 50
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_shift_with_single_spot(self):
        """Should cancel shift with one spot"""
        shift_id = create_shift(
            "Single Spot", "2025-11-25", "12:00", "14:00", 1
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_morning_shift(self):
        """Should cancel early morning shift"""
        shift_id = create_shift(
            "Early Morning", "2025-11-26", "06:00", "10:00", 5
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_evening_shift(self):
        """Should cancel late evening shift"""
        shift_id = create_shift(
            "Late Evening", "2025-11-27", "19:00", "23:00", 4
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_weekend_shift(self):
        """Should cancel weekend shift"""
        shift_id = create_shift(
            "Saturday Event", "2025-11-22", "10:00", "15:00", 8
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cancel_full_day_shift(self):
        """Should cancel full day shift"""
        shift_id = create_shift(
            "All Day Event", "2025-11-28", "09:00", "17:00", 10
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
    
    def test_manager_cancels_own_shift(self):
        """Manager should be able to cancel shift they created"""
        shift_id = create_shift(
            "Manager's Shift", "2025-11-29", "10:00", "14:00", 5
        )
        
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=manager&role=manager"
        )
        
        assert cancel_response.status_code == 200
    
    def test_admin_cancels_manager_shift(self):
        """Admin should be able to cancel any shift"""
        shift_id = create_shift(
            "Manager Created", "2025-11-30", "11:00", "15:00", 6
        )
        
        # Admin cancels manager's shift
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=admin&role=admin"
        )
        
        assert cancel_response.status_code == 200
    
    def test_cannot_cancel_nonexistent_shift(self):
        """Should handle cancellation of non-existent shift gracefully"""
        # Try to cancel shift with ID that doesn't exist
        cancel_response = client.delete(
            f"/api/shifts/99999?cancelled_by=manager&role=manager"
        )
        
        # Should still return 200 (idempotent delete)
        assert cancel_response.status_code == 200
    
    def test_cancel_same_day_multiple_shifts(self):
        """Should cancel multiple shifts on same day"""
        shift1 = create_shift("Morning", "2025-12-01", "08:00", "12:00", 3)
        shift2 = create_shift("Afternoon", "2025-12-01", "13:00", "17:00", 3)
        
        response1 = client.delete(
            f"/api/shifts/{shift1}?cancelled_by=manager&role=manager"
        )
        response2 = client.delete(
            f"/api/shifts/{shift2}?cancelled_by=admin&role=admin"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both removed
        shifts = client.get("/api/shifts").json()
        same_day_shifts = [s for s in shifts if s["date"] == "2025-12-01"]
        assert len(same_day_shifts) == 0
    
    def test_authorization_required_for_cancellation(self):
        """Cancellation requires proper role authorization"""
        shift_id = create_shift(
            "Auth Test", "2025-12-02", "10:00", "14:00", 5
        )
        
        # Try without proper role
        cancel_response = client.delete(
            f"/api/shifts/{shift_id}?cancelled_by=volunteer&role=volunteer"
        )
        
        assert cancel_response.status_code == 403
        
        # Verify shift still exists
        shifts = client.get("/api/shifts").json()
        assert any(s["id"] == shift_id for s in shifts)
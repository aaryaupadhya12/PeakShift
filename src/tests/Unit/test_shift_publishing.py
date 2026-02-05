"""
Test Suite: Shift Publishing
Tests manager's ability to publish validated shifts
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
TEST_DB_PATH = "file:memdb_shift_publishing?mode=memory&cache=shared"
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


def create_and_validate_shift(title, date, start_time, end_time, spots):
    """Helper: Create and validate a shift"""
    create_response = client.post("/api/shifts?created_by=manager", json={
        "title": title,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "spots": spots
    })
    shift_id = create_response.json()["id"]
    client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
    return shift_id


class TestShiftPublishing:
    """Test shift publishing functionality"""
    
    def test_manager_publishes_validated_shift(self):
        """Manager should be able to publish validated shift"""
        shift_id = create_and_validate_shift(
            "Morning Shift", "2025-11-15", "09:00", "13:00", 5
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        data = publish_response.json()
        assert data["status"] == "published"
        assert data["id"] == shift_id
        assert data["published_by"] == "manager"
    
    def test_published_shift_status_changes(self):
        """Shift status should change from validated to published"""
        shift_id = create_and_validate_shift(
            "Status Test", "2025-11-16", "10:00", "14:00", 3
        )
        
        # Verify status is validated before publishing
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "validated"
        
        # Publish
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        # Verify status changed to published
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "published"
    
    def test_publishing_records_manager_username(self):
        """Should record which manager published the shift"""
        shift_id = create_and_validate_shift(
            "Record Test", "2025-11-17", "11:00", "15:00", 4
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["published_by"] == "manager"
    
    def test_publish_multiple_shifts(self):
        """Manager should be able to publish multiple shifts"""
        shift1 = create_and_validate_shift(
            "Shift 1", "2025-11-18", "09:00", "12:00", 3
        )
        shift2 = create_and_validate_shift(
            "Shift 2", "2025-11-19", "13:00", "16:00", 4
        )
        
        response1 = client.post(f"/api/shifts/{shift1}/publish?published_by=manager")
        response2 = client.post(f"/api/shifts/{shift2}/publish?published_by=manager")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both are published
        shifts = client.get("/api/shifts").json()
        published_shifts = [s for s in shifts if s["status"] == "published"]
        assert len(published_shifts) >= 2
    
    def test_publish_shift_with_many_spots(self):
        """Should publish shift with large number of spots"""
        shift_id = create_and_validate_shift(
            "Large Event", "2025-11-20", "08:00", "18:00", 50
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_publish_shift_with_single_spot(self):
        """Should publish shift with only one spot"""
        shift_id = create_and_validate_shift(
            "Single Spot", "2025-11-21", "12:00", "14:00", 1
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_publish_morning_shift(self):
        """Should publish shift scheduled for morning"""
        shift_id = create_and_validate_shift(
            "Early Morning", "2025-11-22", "06:00", "10:00", 5
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_publish_evening_shift(self):
        """Should publish shift scheduled for evening"""
        shift_id = create_and_validate_shift(
            "Late Evening", "2025-11-23", "19:00", "23:00", 4
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_publish_weekend_shift(self):
        """Should publish shift on weekend"""
        shift_id = create_and_validate_shift(
            "Saturday Event", "2025-11-22", "10:00", "15:00", 8
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_publish_full_day_shift(self):
        """Should publish shift spanning full day"""
        shift_id = create_and_validate_shift(
            "All Day Event", "2025-11-25", "09:00", "17:00", 10
        )
        
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
    
    def test_published_shift_appears_in_list(self):
        """Published shift should appear when filtering by status"""
        shift_id = create_and_validate_shift(
            "Filter Test", "2025-11-26", "10:00", "14:00", 5
        )
        
        # Publish
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        # Get published shifts
        all_shifts = client.get("/api/shifts").json()
        published_shifts = [s for s in all_shifts if s["status"] == "published"]
        
        assert any(s["id"] == shift_id for s in published_shifts)
    
    def test_publish_preserves_shift_details(self):
        """Publishing should not modify shift details"""
        shift_id = create_and_validate_shift(
            "Detail Preservation", "2025-11-27", "11:00", "15:00", 7
        )
        
        # Get original details
        original_shifts = client.get("/api/shifts").json()
        original = next(s for s in original_shifts if s["id"] == shift_id)
        
        # Publish
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        # Get updated details
        updated_shifts = client.get("/api/shifts").json()
        updated = next(s for s in updated_shifts if s["id"] == shift_id)
        
        assert updated["title"] == original["title"]
        assert updated["date"] == original["date"]
        assert updated["start_time"] == original["start_time"]
        assert updated["end_time"] == original["end_time"]
        assert updated["spots"] == original["spots"]
        assert updated["created_by"] == original["created_by"]
    
    def test_complete_workflow_draft_to_published(self):
        """Complete workflow: draft → validated → published"""
        # Create draft
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Workflow Test",
            "date": "2025-11-28",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        
        # Verify draft status
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "draft"
        
        # Validate
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        assert validate_response.status_code == 200
        
        # Verify validated status
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "validated"
        
        # Publish
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        assert publish_response.status_code == 200
        
        # Verify published status
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "published"
    
    def test_publish_same_day_multiple_shifts(self):
        """Should publish multiple shifts on the same day"""
        shift1 = create_and_validate_shift(
            "Morning", "2025-11-30", "08:00", "12:00", 3
        )
        shift2 = create_and_validate_shift(
            "Afternoon", "2025-11-30", "13:00", "17:00", 3
        )
        
        response1 = client.post(f"/api/shifts/{shift1}/publish?published_by=manager")
        response2 = client.post(f"/api/shifts/{shift2}/publish?published_by=manager")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both published on same day
        shifts = client.get("/api/shifts").json()
        same_day_published = [
            s for s in shifts 
            if s["date"] == "2025-11-30" and s["status"] == "published"
        ]
        assert len(same_day_published) == 2
    
    def test_published_shifts_visible_to_volunteers(self):
        """Published shifts should be accessible via API"""
        shift_id = create_and_validate_shift(
            "Volunteer Visible", "2025-12-01", "10:00", "14:00", 5
        )
        
        client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        
        # Get all shifts (what volunteers would see)
        all_shifts = client.get("/api/shifts").json()
        published_shift = next(
            (s for s in all_shifts if s["id"] == shift_id), 
            None
        )
        
        assert published_shift is not None
        assert published_shift["status"] == "published"
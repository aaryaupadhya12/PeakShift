"""
Test Suite: Shift Validation
Tests admin's ability to validate draft shifts
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
TEST_DB_PATH = "file:memdb_shift_validation?mode=memory&cache=shared"
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


class TestShiftValidation:
    """Test shift validation functionality"""
    
    def test_admin_validates_draft_shift(self):
        """Admin should be able to validate draft shift"""
        # Create draft shift
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Draft Shift",
            "date": "2025-11-15",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        
        # Validate shift
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        data = validate_response.json()
        assert data["status"] == "validated"
        assert data["id"] == shift_id
        assert data["validated_by"] == "admin"
    
    def test_validated_shift_status_changes(self):
        """Shift status should change from draft to validated"""
        # Create draft shift
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Status Test Shift",
            "date": "2025-11-16",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 3
        })
        shift_id = create_response.json()["id"]
        
        # Verify initial status is draft
        shifts = client.get("/api/shifts").json()
        draft_shift = next(s for s in shifts if s["id"] == shift_id)
        assert draft_shift["status"] == "draft"
        
        # Validate shift
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Verify status changed to validated
        shifts = client.get("/api/shifts").json()
        validated_shift = next(s for s in shifts if s["id"] == shift_id)
        assert validated_shift["status"] == "validated"
    
    def test_validation_records_admin_username(self):
        """Should record which admin validated the shift"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Record Test",
            "date": "2025-11-17",
            "start_time": "11:00",
            "end_time": "15:00",
            "spots": 4
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["validated_by"] == "admin"
    
    def test_validate_multiple_shifts(self):
        """Admin should be able to validate multiple shifts"""
        # Create two draft shifts
        shift1 = client.post("/api/shifts?created_by=manager", json={
            "title": "Shift 1",
            "date": "2025-11-18",
            "start_time": "09:00",
            "end_time": "12:00",
            "spots": 3
        }).json()["id"]
        
        shift2 = client.post("/api/shifts?created_by=manager", json={
            "title": "Shift 2",
            "date": "2025-11-19",
            "start_time": "13:00",
            "end_time": "16:00",
            "spots": 4
        }).json()["id"]
        
        # Validate both
        response1 = client.post(f"/api/shifts/{shift1}/validate?validated_by=admin")
        response2 = client.post(f"/api/shifts/{shift2}/validate?validated_by=admin")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both are validated
        shifts = client.get("/api/shifts").json()
        validated_shifts = [s for s in shifts if s["status"] == "validated"]
        assert len(validated_shifts) >= 2
    
    def test_validate_shift_with_many_spots(self):
        """Should validate shift regardless of spot count"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Large Event",
            "date": "2025-11-20",
            "start_time": "08:00",
            "end_time": "18:00",
            "spots": 50
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validate_morning_shift(self):
        """Should validate shift scheduled for morning"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Early Morning",
            "date": "2025-11-21",
            "start_time": "06:00",
            "end_time": "10:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validate_evening_shift(self):
        """Should validate shift scheduled for evening"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Late Evening",
            "date": "2025-11-22",
            "start_time": "19:00",
            "end_time": "23:00",
            "spots": 4
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validate_weekend_shift(self):
        """Should validate shift on weekend"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Saturday Event",
            "date": "2025-11-22",
            "start_time": "10:00",
            "end_time": "15:00",
            "spots": 8
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validate_full_day_shift(self):
        """Should validate shift spanning full day"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "All Day Event",
            "date": "2025-11-25",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 10
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validated_shift_appears_in_list(self):
        """Validated shift should appear when filtering by status"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Filter Test",
            "date": "2025-11-26",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        
        # Validate
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Get validated shifts
        all_shifts = client.get("/api/shifts").json()
        validated_shifts = [s for s in all_shifts if s["status"] == "validated"]
        
        assert any(s["id"] == shift_id for s in validated_shifts)
    
    def test_validate_shift_preserves_details(self):
        """Validation should not modify shift details"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Detail Preservation Test",
            "date": "2025-11-27",
            "start_time": "11:00",
            "end_time": "15:00",
            "spots": 7
        })
        shift_id = create_response.json()["id"]
        
        # Get original details
        original_shifts = client.get("/api/shifts").json()
        original = next(s for s in original_shifts if s["id"] == shift_id)
        
        # Validate
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Get updated details
        updated_shifts = client.get("/api/shifts").json()
        updated = next(s for s in updated_shifts if s["id"] == shift_id)
        
        assert updated["title"] == original["title"]
        assert updated["date"] == original["date"]
        assert updated["start_time"] == original["start_time"]
        assert updated["end_time"] == original["end_time"]
        assert updated["spots"] == original["spots"]
        assert updated["created_by"] == original["created_by"]
    
    def test_validate_shift_with_single_spot(self):
        """Should validate shift with only one spot"""
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Single Spot Shift",
            "date": "2025-11-28",
            "start_time": "12:00",
            "end_time": "14:00",
            "spots": 1
        })
        shift_id = create_response.json()["id"]
        
        validate_response = client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        assert validate_response.status_code == 200
        assert validate_response.json()["status"] == "validated"
    
    def test_validation_workflow_order(self):
        """Shift must be validated before it can be published"""
        # Create shift
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Workflow Test",
            "date": "2025-11-29",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        
        # Verify starts as draft
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "draft"
        
        # Validate
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Verify now validated
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        assert shift["status"] == "validated"
        
        # Now can be published
        publish_response = client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
        assert publish_response.status_code == 200
        assert publish_response.json()["status"] == "published"
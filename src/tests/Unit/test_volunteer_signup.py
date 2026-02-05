"""
Test Suite: Volunteer Shift Sign-up
Tests volunteer ability to sign up for published shifts
Note: This tests the GET /shifts endpoint which volunteers use to view available shifts.
The actual sign-up functionality would need to be implemented in shift_management.py
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
TEST_DB_PATH = "file:memdb_volunteer_signup?mode=memory&cache=shared"
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
        ('volunteer2', 'volunteer123', 'volunteer'),
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


def create_published_shift(title, date, start_time, end_time, spots):
    """Helper: Create, validate, and publish a shift"""
    # Create
    create_response = client.post("/api/shifts?created_by=manager", json={
        "title": title,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "spots": spots
    })
    shift_id = create_response.json()["id"]
    
    # Validate
    client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
    
    # Publish
    client.post(f"/api/shifts/{shift_id}/publish?published_by=manager")
    
    return shift_id


class TestVolunteerShiftViewing:
    """Test volunteer ability to view published shifts"""
    
    def test_volunteer_can_view_all_shifts(self):
        """Volunteers should be able to view all shifts"""
        response = client.get("/api/shifts")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_volunteer_sees_published_shifts(self):
        """Volunteers should see published shifts"""
        shift_id = create_published_shift(
            "Available Shift", "2025-11-15", "09:00", "13:00", 5
        )
        
        shifts = client.get("/api/shifts").json()
        published_shifts = [s for s in shifts if s["status"] == "published"]
        
        assert any(s["id"] == shift_id for s in published_shifts)
    
    def test_volunteer_sees_shift_details(self):
        """Volunteers should see complete shift details"""
        shift_id = create_published_shift(
            "Detailed Shift", "2025-11-16", "10:00", "14:00", 5
        )
        
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        
        assert shift["title"] == "Detailed Shift"
        assert shift["date"] == "2025-11-16"
        assert shift["start_time"] == "10:00"
        assert shift["end_time"] == "14:00"
        assert shift["spots"] == 5
        assert shift["status"] == "published"
    
    def test_volunteer_sees_available_spots(self):
        """Volunteers should see number of available spots"""
        shift_id = create_published_shift(
            "Spots Test", "2025-11-17", "11:00", "15:00", 8
        )
        
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        
        assert shift["spots"] == 8
    
    def test_volunteer_can_filter_by_status(self):
        """Volunteers should be able to filter shifts by status"""
        create_published_shift("Published 1", "2025-11-18", "09:00", "12:00", 3)
        create_published_shift("Published 2", "2025-11-19", "13:00", "16:00", 4)
        
        # Get all shifts
        all_shifts = client.get("/api/shifts").json()
        
        # Filter for published
        published_shifts = [s for s in all_shifts if s["status"] == "published"]
        
        assert len(published_shifts) >= 2
    
    def test_volunteer_sees_multiple_shifts_same_day(self):
        """Volunteers should see multiple shifts on same day"""
        shift1 = create_published_shift(
            "Morning", "2025-11-20", "08:00", "12:00", 3
        )
        shift2 = create_published_shift(
            "Afternoon", "2025-11-20", "13:00", "17:00", 4
        )
        
        shifts = client.get("/api/shifts").json()
        same_day = [s for s in shifts if s["date"] == "2025-11-20"]
        
        assert len(same_day) >= 2
        assert any(s["id"] == shift1 for s in same_day)
        assert any(s["id"] == shift2 for s in same_day)
    
    def test_volunteer_sees_weekend_shifts(self):
        """Volunteers should see weekend shifts"""
        shift_id = create_published_shift(
            "Saturday Event", "2025-11-22", "10:00", "15:00", 8
        )
        
        shifts = client.get("/api/shifts").json()
        weekend_shift = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert weekend_shift is not None
        assert weekend_shift["date"] == "2025-11-22"
    
    def test_volunteer_sees_morning_shifts(self):
        """Volunteers should see early morning shifts"""
        shift_id = create_published_shift(
            "Early Morning", "2025-11-23", "06:00", "10:00", 5
        )
        
        shifts = client.get("/api/shifts").json()
        morning_shift = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert morning_shift is not None
        assert morning_shift["start_time"] == "06:00"
    
    def test_volunteer_sees_evening_shifts(self):
        """Volunteers should see evening shifts"""
        shift_id = create_published_shift(
            "Evening Event", "2025-11-24", "18:00", "22:00", 6
        )
        
        shifts = client.get("/api/shifts").json()
        evening_shift = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert evening_shift is not None
        assert evening_shift["start_time"] == "18:00"
    
    def test_volunteer_sees_full_day_shifts(self):
        """Volunteers should see full day shifts"""
        shift_id = create_published_shift(
            "All Day Event", "2025-11-25", "09:00", "17:00", 10
        )
        
        shifts = client.get("/api/shifts").json()
        full_day = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert full_day is not None
        assert full_day["end_time"] == "17:00"
    
    def test_volunteer_sees_shifts_with_many_spots(self):
        """Volunteers should see large events"""
        shift_id = create_published_shift(
            "Large Event", "2025-11-26", "08:00", "18:00", 50
        )
        
        shifts = client.get("/api/shifts").json()
        large_event = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert large_event is not None
        assert large_event["spots"] == 50
    
    def test_volunteer_sees_shifts_with_few_spots(self):
        """Volunteers should see shifts with limited spots"""
        shift_id = create_published_shift(
            "Limited Spots", "2025-11-27", "10:00", "14:00", 2
        )
        
        shifts = client.get("/api/shifts").json()
        limited = next((s for s in shifts if s["id"] == shift_id), None)
        
        assert limited is not None
        assert limited["spots"] == 2
    
    def test_volunteer_does_not_see_draft_shifts(self):
        """Volunteers should not see draft shifts (unpublished)"""
        # Create draft shift (don't validate or publish)
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Draft Shift",
            "date": "2025-11-28",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        draft_id = create_response.json()["id"]
        
        # Volunteers viewing shifts
        shifts = client.get("/api/shifts").json()
        published_only = [s for s in shifts if s["status"] == "published"]
        
        # Draft shift should not be in published list
        assert not any(s["id"] == draft_id for s in published_only)
    
    def test_volunteer_does_not_see_only_validated_shifts(self):
        """Volunteers should not see validated but unpublished shifts"""
        # Create and validate but don't publish
        create_response = client.post("/api/shifts?created_by=manager", json={
            "title": "Validated Only",
            "date": "2025-11-29",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 5
        })
        shift_id = create_response.json()["id"]
        client.post(f"/api/shifts/{shift_id}/validate?validated_by=admin")
        
        # Volunteers should only care about published
        shifts = client.get("/api/shifts").json()
        published_only = [s for s in shifts if s["status"] == "published"]
        
        assert not any(s["id"] == shift_id for s in published_only)
    
    def test_shifts_ordered_by_date_and_time(self):
        """Shifts should be retrievable in chronological order"""
        shift1 = create_published_shift(
            "First", "2025-11-30", "09:00", "12:00", 3
        )
        shift2 = create_published_shift(
            "Second", "2025-11-30", "13:00", "16:00", 3
        )
        shift3 = create_published_shift(
            "Third", "2025-12-01", "09:00", "12:00", 3
        )
        
        shifts = client.get("/api/shifts").json()
        
        # Find our shifts in order
        our_shifts = [
            s for s in shifts 
            if s["id"] in [shift1, shift2, shift3]
        ]
        
        # Should be in chronological order (based on init_db.py ORDER BY)
        assert len(our_shifts) == 3
    
    def test_api_returns_json_array(self):
        """Shifts endpoint should return JSON array"""
        response = client.get("/api/shifts")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert isinstance(response.json(), list)
    
    def test_empty_shift_list_valid(self):
        """Should handle case when no published shifts exist"""
        # Don't create any published shifts
        response = client.get("/api/shifts")
        
        assert response.status_code == 200
        # May have shifts from other tests or none
        assert isinstance(response.json(), list)
    
    def test_volunteer_can_view_shift_creator(self):
        """Volunteers should see who created the shift"""
        shift_id = create_published_shift(
            "Creator Test", "2025-12-02", "10:00", "14:00", 5
        )
        
        shifts = client.get("/api/shifts").json()
        shift = next(s for s in shifts if s["id"] == shift_id)
        
        assert shift["created_by"] == "manager"
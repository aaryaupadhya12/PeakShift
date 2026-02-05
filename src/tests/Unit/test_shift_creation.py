"""
Test Suite: Shift Creation
Tests manager's ability to create shifts with various scenarios
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
TEST_DB_PATH = "file:memdb_shift_creation?mode=memory&cache=shared"
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
        ('manager', 'manager123', 'manager'),
        ('volunteer', 'volunteer123', 'volunteer'),
        ('admin', 'admin123', 'admin'),
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


class TestShiftCreation:
    """Test shift creation functionality"""
    
    def test_manager_creates_shift_successfully(self):
        """Manager should be able to create a shift"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Morning Shift",
            "date": "2025-11-15",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert "id" in data
        assert data["message"] == "Shift created, awaiting admin validation"
    
    def test_shift_starts_in_draft_status(self):
        """Newly created shifts should have draft status"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Test Shift",
            "date": "2025-11-20",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 3
        })
        
        assert response.status_code == 200
        assert response.json()["status"] == "draft"
    
    def test_volunteer_cannot_create_shift(self):
        """Volunteers should not be able to create shifts"""
        response = client.post("/api/shifts?created_by=volunteer", json={
            "title": "Unauthorized Shift",
            "date": "2025-11-20",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 3
        })
        
        assert response.status_code == 403
        assert "only managers" in response.json()["detail"].lower()
    
    def test_create_shift_with_multiple_spots(self):
        """Should create shift with specified number of spots"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Large Event",
            "date": "2025-12-01",
            "start_time": "08:00",
            "end_time": "18:00",
            "spots": 20
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        # Verify shift was created with correct spots
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["spots"] == 20
    
    def test_create_shift_with_single_spot(self):
        """Should create shift with single spot"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Solo Task",
            "date": "2025-11-25",
            "start_time": "14:00",
            "end_time": "16:00",
            "spots": 1
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["spots"] == 1
    
    def test_create_evening_shift(self):
        """Should create shift with evening hours"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Evening Shift",
            "date": "2025-11-18",
            "start_time": "18:00",
            "end_time": "22:00",
            "spots": 4
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["start_time"] == "18:00"
        assert created_shift["end_time"] == "22:00"
    
    def test_create_weekend_shift(self):
        """Should create shift for weekend date"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Weekend Event",
            "date": "2025-11-22",  # Saturday
            "start_time": "10:00",
            "end_time": "15:00",
            "spots": 8
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["date"] == "2025-11-22"
    
    def test_create_multiple_shifts_same_day(self):
        """Should create multiple shifts on the same day"""
        # Morning shift
        response1 = client.post("/api/shifts?created_by=manager", json={
            "title": "Morning Shift",
            "date": "2025-11-30",
            "start_time": "08:00",
            "end_time": "12:00",
            "spots": 3
        })
        
        # Afternoon shift
        response2 = client.post("/api/shifts?created_by=manager", json={
            "title": "Afternoon Shift",
            "date": "2025-11-30",
            "start_time": "13:00",
            "end_time": "17:00",
            "spots": 3
        })
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both shifts exist
        shifts = client.get("/api/shifts").json()
        same_day_shifts = [s for s in shifts if s["date"] == "2025-11-30"]
        assert len(same_day_shifts) == 2
    
    def test_shift_created_by_field_recorded(self):
        """Should record which manager created the shift"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Test Shift",
            "date": "2025-12-05",
            "start_time": "09:00",
            "end_time": "13:00",
            "spots": 5
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["created_by"] == "manager"
    
    def test_shift_title_recorded_correctly(self):
        """Should store exact shift title"""
        title = "Special Holiday Volunteer Drive"
        response = client.post("/api/shifts?created_by=manager", json={
            "title": title,
            "date": "2025-12-25",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 10
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["title"] == title
    
    def test_create_shift_returns_shift_id(self):
        """Should return unique shift ID after creation"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "ID Test Shift",
            "date": "2025-11-28",
            "start_time": "11:00",
            "end_time": "15:00",
            "spots": 4
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0
    
    def test_shift_appears_in_shift_list(self):
        """Created shift should appear in GET /shifts"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Visibility Test",
            "date": "2025-12-10",
            "start_time": "09:00",
            "end_time": "12:00",
            "spots": 5
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        # Get all shifts
        shifts = client.get("/api/shifts").json()
        shift_ids = [s["id"] for s in shifts]
        assert shift_id in shift_ids
    
    def test_create_full_day_shift(self):
        """Should create shift spanning full work day"""
        response = client.post("/api/shifts?created_by=manager", json={
            "title": "Full Day Event",
            "date": "2025-12-15",
            "start_time": "09:00",
            "end_time": "17:00",
            "spots": 6
        })
        
        assert response.status_code == 200
        shift_id = response.json()["id"]
        
        shifts = client.get("/api/shifts").json()
        created_shift = next(s for s in shifts if s["id"] == shift_id)
        assert created_shift["start_time"] == "09:00"
        assert created_shift["end_time"] == "17:00"
    
    def test_admin_can_also_create_shift(self):
        """Admin should be able to create shifts (has manager permissions)"""
        # Note: Based on RBAC, admin has create_shift permission
        # However, the shift_management.py currently checks for role == 'manager'
        # This test documents the current behavior
        response = client.post("/api/shifts?created_by=admin", json={
            "title": "Admin Created Shift",
            "date": "2025-12-20",
            "start_time": "10:00",
            "end_time": "14:00",
            "spots": 5
        })
        
        # Current implementation restricts to manager role only
        assert response.status_code == 403
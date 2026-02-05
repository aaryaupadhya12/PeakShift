# Developer Documentation

## Project Structure
```
src/
├── backend/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── role_based_access.py
│   │   ├── two_factor_auth.py
│   │   ├── user_lockout.py
│   │   ├── user_login.py
│   │   └── shift_management.py
│   ├── config.py
│   ├── init_db.py
│   ├── main.py
│   └── manager_coverage_report.py
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── ShiftDashboard.js
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
└── tests/
    ├── test_together.py
    ├── Unit/
    │   └── test_manager_coverage_report.py
    └── System/
        └── (system tests)
```

## Setup

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
cd src/backend
python init_db.py
```

### Frontend
```bash
cd src/frontend
npm install
```

## Running Application

### Start Backend
```bash
cd src/backend
uvicorn main:app --reload
```
Access: http://localhost:8000
API Docs: http://localhost:8000/docs

### Start Frontend
```bash
cd src/frontend
npm start
```
Access: http://localhost:3000

## Testing
```bash
cd src
pytest tests/test_together.py -v
```
Expected: All tests pass (32+ tests covering auth, RBAC, lockout, OTP, shifts, and manager coverage reports)

**Note:** CI/CD pipeline only runs `test_together.py`. Unit and System test folders are for local development only.

## Default Credentials
- Admin: admin / admin123 (2FA required)
- Manager: manager / manager123
- Volunteer: volunteer / volunteer123

## Database Schema

### Users Table
```sql
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
```

**Credits System:**
- Volunteers earn 1 credit per approved shift
- Managers can use credits for preferential selection
- Credits persist across sessions

### Shifts Table
```sql
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
```

### Volunteer Commitments Table
```sql
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
```

**Commitment Statuses:**
- `pending`: Awaiting manager approval
- `approved`: Manager approved, volunteer can participate
- `rejected`: Manager rejected the signup
- `cancelled`: Volunteer cancelled within allowed window

## Technology Stack
- Backend: FastAPI, SQLite, Python 3.9+
- Frontend: React 18, JavaScript
- Testing: Pytest
- CI/CD: GitHub Actions

## Development Workflow
1. Create feature branch from develop
2. Write code and tests
3. Run tests locally: `pytest tests/test_together.py -v`
4. Commit with conventional commits (feat:, fix:, docs:, etc.)
5. Push to feature branch
6. Create pull request to develop
7. Wait for CI/CD checks to pass
8. Request team review
9. Merge after approval

## Key Features

### Authentication & Security
- Password hashing (SHA-256)
- Two-factor authentication for admins
- Account lockout after 3 failed attempts (15-minute lockout)
- OTP expires after 5 minutes

### Role-Based Access Control
- **Admin**: Full access (manage users, validate shifts, all manager permissions)
- **Manager**: Create, publish, delete shifts + volunteer permissions
- **Volunteer**: View and sign up for shifts

### Shift Management Workflow
1. Manager creates shift → Status: `draft`
2. Admin validates shift → Status: `validated`
3. Manager publishes shift → Status: `published`
4. Volunteers can sign up for published shifts
5. Manager/Admin can cancel shifts

### Volunteer Signup & Approval Flow
1. Volunteer signs up for published shift → Commitment: `pending`
2. System checks for overlapping shifts (same date/time)
3. If overlap detected, suggest alternative shifts
4. Manager reviews and approves/rejects → Commitment: `approved` or `rejected`
5. On approval:
   - Available spots decremented
   - Volunteer earns 1 credit
   - 12-hour cancellation window starts
6. Volunteer can cancel within window → Commitment: `cancelled`, spot restored

### Manager Coverage Reports
- Filter shifts by date range and location
- Show fill status for each shift (filled/unfilled)
- Calculate participation rates per staff member
- Export reports to CSV format
- Module: `backend/manager_coverage_report.py`

## Common Commands

### Backend
```bash
# Initialize database
python src/backend/init_db.py

# Run server with reload (from src directory)
cd src
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run tests (CI/CD tests only)
cd src
pytest tests/test_together.py -v

# Run unit tests (development only)
cd src
pytest tests/Unit/test_manager_coverage_report.py -v

# Run tests with coverage
cd src
pytest tests/test_together.py --cov=backend --cov-report=xml

# Run linter
cd src
python -m pylint backend/manager_coverage_report.py

# Run security scan
cd src
bandit -r backend/manager_coverage_report.py
```

### Frontend
```bash
# Install dependencies
cd src/frontend && npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## API Endpoints Summary

### Authentication
- POST `/api/auth/login`
- POST `/api/auth/generate-otp`
- POST `/api/auth/verify-otp`

### Account Management
- GET `/api/auth/check-lockout/{username}`
- POST `/api/auth/record-failed-attempt`
- POST `/api/auth/reset-attempts`

### RBAC
- GET `/api/rbac/roles/{role}/permissions`
- GET `/api/rbac/check-permission`
- POST `/api/rbac/validate-action`

### Shift Management
- POST `/api/shifts`
- POST `/api/shifts/{shift_id}/validate`
- POST `/api/shifts/{shift_id}/publish`
- DELETE `/api/shifts/{shift_id}`
- GET `/api/shifts`
- POST `/api/shifts/{shift_id}/volunteer`

### Volunteer Commitments
- POST `/api/volunteer-commitments/{commitment_id}/approve`
- POST `/api/volunteer-commitments/{commitment_id}/cancel`
- GET `/api/volunteer-commitments`

### Manager Coverage Reports
- POST `/api/reports/coverage`
- POST `/api/reports/coverage/export`

## Testing Guidelines

### Test Coverage
- Authentication: Login success/failure, role validation
- Two-Factor Auth: OTP generation, verification, expiration
- Account Lockout: Failed attempts, lockout mechanism, reset
- RBAC: Permission checks, role validation, action authorization
- Shift Management: Create, validate, publish, cancel, unauthorized actions
- Manager Coverage Reports: Filtering, fill status, participation rates, CSV export

### Running Specific Tests
```bash
# Run all CI/CD tests
cd src
pytest tests/test_together.py -v

# Run specific test class
cd src
pytest tests/test_together.py::TestShiftManagement -v

# Run specific test
cd src
pytest tests/test_together.py::TestShiftManagement::test_create_shift -v

# Run unit tests (development only)
cd src
pytest tests/Unit/test_manager_coverage_report.py -v
```

## Environment Variables
- `TEST_MODE`: Set to "1" for in-memory database during testing
- `TEST_DB_PATH`: Custom database path for tests
- `REACT_APP_API_URL`: Frontend API URL (default: http://localhost:8000/api)

## Troubleshooting

### Backend Issues
- **Database locked**: Close all database connections, restart server
- **Import errors**: Ensure `src/` is in PYTHONPATH
- **Port 8000 in use**: Kill process or use different port

### Frontend Issues
- **API connection fails**: Verify backend is running on port 8000
- **CORS errors**: Check CORS middleware in `main.py`
- **Build fails**: Delete `node_modules`, run `npm install` again

## Contact
- Scrum Master: @pes1ug23am006-dot
- Developer Team: @Anshullmudyavar1, @aaravadarsh18, @AHaveeshKumar
- Teaching Assistants: @jash00007, @nh2seven
- Faculty Supervisor: @prakasheeralli
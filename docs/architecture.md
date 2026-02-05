# System Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture Pattern](#architecture-pattern)
3. [System Components](#system-components)
4. [Technology Stack](#technology-stack)
5. [Directory Structure](#directory-structure)
6. [Data Flow](#data-flow)
7. [Database Architecture](#database-architecture)
8. [API Architecture](#api-architecture)
9. [Frontend Architecture](#frontend-architecture)
10. [Security Architecture](#security-architecture)
11. [Deployment Architecture](#deployment-architecture)

---

## Overview

The Helping Hands Volunteer Management System is a full-stack web application built using a client-server architecture. The system facilitates volunteer shift management for retail stores during busy periods, implementing comprehensive authentication, authorization, and workflow management.

**Key Characteristics:**
- Three-tier architecture (Presentation, Business Logic, Data)
- RESTful API design
- Role-based access control (RBAC)
- Event-driven user interface
- SQLite database with automatic migrations
- Modular and extensible design

---

## Architecture Pattern

### Architectural Style: Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION TIER                        │
│                    (React Frontend)                          │
│  - User Interface Components                                 │
│  - State Management                                          │
│  - Client-side Routing                                       │
│  - HTTP Client (Fetch API)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/HTTPS
                       │ REST API Calls
┌──────────────────────▼──────────────────────────────────────┐
│                    BUSINESS LOGIC TIER                       │
│                    (FastAPI Backend)                         │
│  - API Endpoints                                             │
│  - Business Logic                                            │
│  - Authentication & Authorization                            │
│  - Data Validation                                           │
│  - Report Generation                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ SQL Queries
                       │ ORM Operations
┌──────────────────────▼──────────────────────────────────────┐
│                       DATA TIER                              │
│                    (SQLite Database)                         │
│  - User Data                                                 │
│  - Shift Data                                                │
│  - Commitment Data                                           │
│  - Session Data                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Frontend Layer (React SPA)

**Purpose:** Provides the user interface for all user roles

**Key Components:**
- **App.js** - Main application component, handles authentication state
- **ShiftDashboard.js** - Primary dashboard component with role-specific views
- **Login Form** - User authentication interface
- **OTP Verification** - Two-factor authentication for admins
- **Shift Management UI** - Create, view, and manage shifts
- **Coverage Reports** - Manager reporting interface

**Responsibilities:**
- Render user interface
- Handle user interactions
- Manage client-side state
- Make API calls to backend
- Display data and feedback to users
- Client-side validation

### 2. Backend Layer (FastAPI Application)

**Purpose:** Handles business logic, data processing, and API endpoints

**Key Modules:**

#### Core Application (`main.py`)
- Application initialization
- Middleware configuration (CORS)
- Router registration
- Database initialization
- Startup event handlers
- Health check endpoints

#### Authentication Module (`auth/`)

**user_login.py**
- User authentication
- Password verification (SHA-256 hashing)
- Session management
- Login response with user details and credits

**two_factor_auth.py**
- OTP generation for admin users
- OTP verification
- Time-based expiration (5 minutes)
- Secure random OTP generation

**user_lockout.py**
- Failed login attempt tracking
- Account lockout mechanism (3 attempts)
- Automatic unlock after 15 minutes
- Lockout status checking

**role_based_access.py**
- Permission definitions per role
- Permission checking logic
- Action validation
- Role-based filtering

**shift_management.py**
- Shift CRUD operations
- Volunteer signup logic
- Commitment approval/rejection
- Shift overlap detection
- Alternative shift suggestions
- Cancellation logic
- Rate limiting

**manager_reports.py**
- Coverage report generation API
- CSV export functionality
- Integration with report generation module

#### Business Logic Module

**manager_coverage_report.py**
- Report generation logic
- Data filtering by date range and location
- Fill status calculation
- Participation rate computation
- CSV formatting and export

#### Configuration Module (`config.py`)
- Database connection management
- Application settings
- Environment configuration

### 3. Data Layer (SQLite Database)

**Purpose:** Persistent storage for all application data

**Database File:** `helping_hands.db`

**Connection Management:**
- Connection pooling via `config.py`
- Row factory for dict-like access
- Automatic connection handling

---

## Technology Stack

### Frontend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| JavaScript | ES6+ | Programming language |
| CSS3 | - | Styling |
| Fetch API | Native | HTTP client |
| Node.js | 24.11.0 | Runtime environment |
| npm | Latest | Package manager |

### Backend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11.0 | Programming language |
| FastAPI | Latest | Web framework |
| Pydantic | Latest | Data validation |
| SQLite | 3.x | Database |
| Uvicorn | Latest | ASGI server |
| hashlib | Standard | Password hashing |

### Development & Testing

| Tool | Purpose |
|------|---------|
| pytest | Unit and integration testing |
| pylint | Code quality analysis |
| bandit | Security scanning |
| Git | Version control |
| GitHub Actions | CI/CD pipeline |

---

## Directory Structure

```
temp-bugfix/
│
├── src/                           # Source code root
│   ├── backend/                   # Backend application
│   │   ├── main.py               # Application entry point
│   │   ├── config.py             # Database configuration
│   │   ├── init_db.py            # Database initialization
│   │   ├── manager_coverage_report.py  # Report logic
│   │   └── auth/                 # Authentication modules
│   │       ├── user_login.py
│   │       ├── two_factor_auth.py
│   │       ├── user_lockout.py
│   │       ├── role_based_access.py
│   │       ├── shift_management.py
│   │       └── manager_reports.py
│   │
│   ├── frontend/                 # Frontend application
│   │   ├── public/
│   │   │   └── index.html       # HTML template
│   │   ├── src/
│   │   │   ├── App.js           # Main component
│   │   │   ├── App.css          # App styles
│   │   │   ├── ShiftDashboard.js  # Dashboard component
│   │   │   ├── ShiftDashboard.css # Dashboard styles
│   │   │   ├── index.js         # Entry point
│   │   │   └── index.css        # Global styles
│   │   └── package.json         # Dependencies
│   │
│   └── tests/                    # Test suite
│       ├── test_together.py     # Integration tests
│       ├── Unit/                # Unit tests
│       │   ├── test_shift_creation.py
│       │   ├── test_shift_validation.py
│       │   ├── test_shift_publishing.py
│       │   ├── test_volunteer_signup.py
│       │   ├── test_credit_increment.py
│       │   ├── test_credits_column_creation.py
│       │   ├── test_login_returns_credits.py
│       │   ├── test_manager_coverage_report.py
│       │   └── test_shift_cancellation.py
│       └── System/              # System tests
│           ├── test_volunteer_approval_flow.py
│           ├── test_overlapping_shifts.py
│           └── test_credits_display_ui.py
│
├── docs/                         # Documentation
│   ├── API_documentation.md
│   ├── Developer_Guide.md
│   ├── user_guide.md
│   ├── stories.md
│   └── architecture.md
│
├── README.md                     # Project overview
├── requirements.txt              # Python dependencies
└── run.py                        # Application launcher
```

---

## Data Flow

### Request-Response Flow

```
User Action → Frontend Component → API Call → Backend Endpoint → 
Database Query → Data Processing → Response → Frontend Update → 
UI Render
```

### Detailed Flow Examples

#### 1. User Login Flow

```
1. User enters credentials in Login Form
   ↓
2. Frontend calls POST /api/auth/login
   ↓
3. Backend validates credentials against users table
   ↓
4. If admin: Backend generates OTP
   ↓
5. Backend returns user data + role (+ OTP if admin)
   ↓
6. Frontend stores user state
   ↓
7. If admin: Frontend displays OTP verification screen
   ↓
8. Admin enters OTP
   ↓
9. Frontend calls POST /api/auth/verify-otp
   ↓
10. Backend validates OTP
   ↓
11. Frontend displays dashboard
```

#### 2. Shift Creation Flow

```
1. Manager fills shift creation form
   ↓
2. Frontend validates form data
   ↓
3. Frontend calls POST /api/shifts?created_by=manager
   ↓
4. Backend validates manager role
   ↓
5. Backend inserts shift with status='draft'
   ↓
6. Backend returns shift ID and confirmation
   ↓
7. Frontend refreshes shift list
   ↓
8. Frontend displays success message
```

#### 3. Volunteer Signup Flow

```
1. Volunteer clicks "Sign Up" on published shift
   ↓
2. Frontend calls POST /api/shifts/{id}/volunteer
   ↓
3. Backend validates volunteer role
   ↓
4. Backend checks if shift is published
   ↓
5. Backend checks for existing commitments
   ↓
6. Backend checks for overlapping shifts
   ↓
7. If overlap: Backend returns alternative shifts
   ↓
8. If no overlap: Backend creates commitment (status='pending')
   ↓
9. Backend returns confirmation
   ↓
10. Frontend refreshes commitments list
   ↓
11. Frontend displays pending status
```

#### 4. Coverage Report Generation Flow

```
1. Manager sets date/location filters
   ↓
2. Frontend calls POST /api/reports/coverage
   ↓
3. Backend queries shifts table with filters
   ↓
4. Backend queries volunteer_commitments table
   ↓
5. Backend calculates fill status per shift
   ↓
6. Backend calculates participation rates
   ↓
7. Backend formats report data
   ↓
8. Backend returns JSON report
   ↓
9. Frontend renders report tables
   ↓
10. User clicks "Export to CSV"
   ↓
11. Frontend calls POST /api/reports/coverage/export
   ↓
12. Backend converts report to CSV format
   ↓
13. Backend returns CSV file
   ↓
14. Frontend triggers download
```

---

## Database Architecture

### Entity-Relationship Diagram

```
┌─────────────────────┐
│       USERS         │
├─────────────────────┤
│ username (PK)       │
│ password            │
│ role                │
│ attempts            │
│ locked_until        │
│ otp                 │
│ otp_expires         │
│ credits             │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────────┐
│        SHIFTS               │
├─────────────────────────────┤
│ id (PK)                     │
│ title                       │
│ date                        │
│ start_time                  │
│ end_time                    │
│ spots                       │
│ location                    │
│ volunteers                  │
│ status                      │
│ created_by (FK → users)     │
└──────────┬──────────────────┘
           │
           │ 1:N
           │
┌──────────▼────────────────────────┐
│   VOLUNTEER_COMMITMENTS           │
├───────────────────────────────────┤
│ id (PK)                           │
│ username (FK → users)             │
│ shift_id (FK → shifts)            │
│ volunteered_at                    │
│ status                            │
│ approved_at                       │
│ approved_by (FK → users)          │
│ can_cancel_until                  │
└───────────────────────────────────┘
```

### Table Specifications

#### USERS Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| username | TEXT | PRIMARY KEY | Unique user identifier |
| password | TEXT | NOT NULL | SHA-256 hashed password |
| role | TEXT | CHECK IN ('admin', 'manager', 'volunteer') | User role |
| attempts | INTEGER | DEFAULT 0 | Failed login counter |
| locked_until | TEXT | NULLABLE | Lockout expiration timestamp |
| otp | TEXT | NULLABLE | Current OTP code |
| otp_expires | TEXT | NULLABLE | OTP expiration timestamp |
| credits | INTEGER | DEFAULT 0 | Volunteer reward points |

#### SHIFTS Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique shift identifier |
| title | TEXT | NOT NULL | Shift name/description |
| date | TEXT | NOT NULL | Shift date (YYYY-MM-DD) |
| start_time | TEXT | NOT NULL | Start time (HH:MM) |
| end_time | TEXT | NOT NULL | End time (HH:MM) |
| spots | INTEGER | NOT NULL | Required volunteer count |
| location | TEXT | NULLABLE | Store/location identifier |
| volunteers | TEXT | DEFAULT '[]' | Legacy field (JSON array) |
| status | TEXT | DEFAULT 'draft' | Workflow status |
| created_by | TEXT | FOREIGN KEY → users.username | Creator username |

**Status Values:**
- `draft` - Created but not validated
- `validated` - Approved by admin
- `published` - Available for signup

#### VOLUNTEER_COMMITMENTS Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique commitment ID |
| username | TEXT | FOREIGN KEY → users.username | Volunteer username |
| shift_id | INTEGER | FOREIGN KEY → shifts.id | Associated shift |
| volunteered_at | TEXT | NOT NULL | Signup timestamp |
| status | TEXT | DEFAULT 'pending' | Commitment status |
| approved_at | TEXT | NULLABLE | Approval timestamp |
| approved_by | TEXT | FOREIGN KEY → users.username | Approver username |
| can_cancel_until | TEXT | NULLABLE | Cancellation deadline |

**Status Values:**
- `pending` - Awaiting manager approval
- `approved` - Manager approved
- `rejected` - Manager rejected
- `cancelled` - Volunteer cancelled

### Database Migrations

**Migration Strategy:** Schema evolution handled in `main.py` startup

```python
# Migration pseudocode
ON STARTUP:
    CREATE TABLES IF NOT EXISTS
    
    FOR each required column:
        IF column does not exist:
            ALTER TABLE ADD COLUMN
            LOG migration
    
    INSERT default admin user IF NOT EXISTS
```

**Migration History:**
1. Initial schema (users, shifts, volunteer_commitments)
2. Added `credits` column to users table
3. Added `location` column to shifts table
4. Enhanced volunteer_commitments with approval workflow fields

---

## API Architecture

### API Design Principles

1. **RESTful Design** - Resources identified by URLs, HTTP methods for actions
2. **Stateless** - Each request contains all necessary information
3. **JSON Communication** - Request and response bodies in JSON format
4. **Error Handling** - Consistent error response structure
5. **Rate Limiting** - Prevent abuse of API endpoints

### API Structure

```
/api
├── /auth                    # Authentication endpoints
│   ├── POST /login
│   ├── POST /generate-otp
│   ├── POST /verify-otp
│   ├── GET /check-lockout/{username}
│   ├── POST /record-failed-attempt
│   └── POST /reset-attempts
│
├── /rbac                    # Authorization endpoints
│   ├── GET /roles/{role}/permissions
│   ├── GET /check-permission
│   └── POST /validate-action
│
├── /shifts                  # Shift management
│   ├── POST /shifts
│   ├── POST /shifts/{id}/validate
│   ├── POST /shifts/{id}/publish
│   ├── POST /shifts/{id}/volunteer
│   ├── DELETE /shifts/{id}
│   └── GET /shifts
│
├── /volunteer-commitments   # Commitment management
│   ├── POST /{id}/approve
│   ├── POST /{id}/cancel
│   └── GET /
│
└── /reports                 # Reporting endpoints
    ├── POST /coverage
    └── POST /coverage/export
```

### API Authentication Flow

```
Request → Rate Limiter → Role Validator → Business Logic → 
Database → Response Formatter → Client
```

### Error Response Format

```json
{
  "detail": "Error message explaining what went wrong"
}
```

**HTTP Status Codes Used:**
- 200: Success
- 400: Bad Request (validation error)
- 403: Forbidden (permission denied)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error

---

## Frontend Architecture

### Component Hierarchy

```
App (Root)
├── Login Form
│   └── OTP Verification (conditional)
│
└── ShiftDashboard (authenticated)
    ├── User Info Header
    │   ├── Username Display
    │   ├── Role Display
    │   ├── Credits Display (volunteers)
    │   └── Logout Button
    │
    ├── Create Shift Form (managers only)
    │   ├── Title Input
    │   ├── Date Input
    │   ├── Time Inputs
    │   ├── Spots Input
    │   ├── Location Input
    │   └── Submit Button
    │
    ├── Coverage Report Section (managers only)
    │   ├── Filter Form
    │   │   ├── Start Date Input
    │   │   ├── End Date Input
    │   │   └── Location Input
    │   ├── Generate Button
    │   ├── Export Button
    │   └── Report Display
    │       ├── Summary Stats
    │       ├── Shift Fill Table
    │       └── Participation Table
    │
    ├── My Commitments (volunteers only)
    │   └── Commitment Cards
    │       ├── Shift Details
    │       ├── Status Badge
    │       └── Cancel Button (conditional)
    │
    ├── Alternative Shifts Modal (conditional)
    │   └── Shift Cards
    │       └── Sign Up Buttons
    │
    └── Shift List
        └── Shift Cards
            ├── Shift Details
            ├── Status Badge
            ├── Validate Button (admins)
            ├── Publish Button (managers)
            ├── Cancel Button (managers/admins)
            ├── Pending Volunteers (managers)
            │   └── Approve/Reject Buttons
            └── Sign Up Button (volunteers)
```

### State Management

**State Location:** Component-level state using React hooks

**State Variables:**
- `user` - Current authenticated user object
- `shifts` - Array of shift objects
- `volunteerCommitments` - Array of volunteer's commitments
- `message` - UI feedback message object
- `newShift` - Form state for shift creation
- `coverageReport` - Report data object
- `reportFilters` - Filter state for reports
- `showCoverageReport` - Boolean toggle
- `showAlternatives` - Boolean toggle
- `alternativeShifts` - Array of alternative shift objects

### Data Fetching Strategy

**Pattern:** Fetch on mount and after mutations

```javascript
useEffect(() => {
  fetchShifts();
  fetchCommitments();
}, []);

// After create/update/delete:
fetchShifts();
fetchCommitments();
```

### Styling Architecture

**Approach:** Component-scoped CSS files

**Style Organization:**
- `App.css` - Authentication UI styles
- `ShiftDashboard.css` - Dashboard and shift management styles
- `index.css` - Global styles and resets

**Design System:**
- Color Palette: Blue primary, green success, red error, yellow warning
- Typography: System fonts with size hierarchy
- Spacing: 8px base unit
- Border Radius: 6-10px for cards and buttons
- Shadows: Subtle elevation with box-shadow

---

## Security Architecture

### Authentication Security

**Password Storage:**
- SHA-256 hashing algorithm
- Passwords never stored in plain text
- Hash comparison for verification

**Session Management:**
- Client-side user state storage
- No server-side session persistence
- Token-free architecture (suitable for prototype)

**Two-Factor Authentication:**
- Random 6-digit OTP generation
- 5-minute expiration window
- Single-use verification
- Admin-only requirement

### Authorization Security

**Role-Based Access Control:**
- Permission definitions stored in backend
- Every sensitive operation checks permissions
- Database-level role validation
- Frontend UI adapts to user role

**Rate Limiting:**
- In-memory rate limiter
- 10 requests per 60-second window per IP
- Prevents brute force attacks
- Returns 429 status when exceeded

### Account Security

**Lockout Mechanism:**
- Automatic lockout after 3 failed attempts
- 15-minute lockout duration
- Persistent across sessions
- Reset on successful login

**Data Validation:**
- Input validation on frontend and backend
- Pydantic models for request validation
- SQL injection prevention via parameterized queries
- XSS prevention via React's automatic escaping

### Security Best Practices Implemented

1. **Principle of Least Privilege** - Users only access what they need
2. **Defense in Depth** - Multiple layers of security controls
3. **Fail Securely** - Errors don't expose sensitive information
4. **Separation of Concerns** - Authentication separate from authorization
5. **Audit Trail** - Tracking who performed actions (approved_by, created_by)

---

## Deployment Architecture

### Development Environment

```
Local Machine
├── Backend Server (Uvicorn)
│   └── Port 8000
│   └── Auto-reload enabled
│
└── Frontend Dev Server (React)
    └── Port 3000
    └── Hot module replacement
```

**Development Workflow:**
1. Start backend: `cd src && python -m uvicorn backend.main:app --reload`
2. Start frontend: `cd src/frontend && npm start`
3. Access application: `http://localhost:3000`
4. Backend API: `http://localhost:8000`

### Production Environment (Recommended)

```
Production Server
├── Reverse Proxy (Nginx)
│   ├── Routes /api/* to Backend
│   ├── Routes /* to Frontend
│   └── Handles SSL/TLS
│
├── Backend (Uvicorn/Gunicorn)
│   └── Multiple workers
│   └── Process manager (systemd/supervisor)
│
├── Frontend (Static Files)
│   └── Built React app
│   └── Served by Nginx
│
└── Database (SQLite or PostgreSQL)
    └── Regular backups
    └── Data persistence
```

### Containerization (Docker - Optional)

```dockerfile
# Backend Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/backend ./backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]

# Frontend Dockerfile
FROM node:24
WORKDIR /app
COPY src/frontend/package*.json ./
RUN npm install
COPY src/frontend .
RUN npm run build
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
```

### Continuous Integration/Continuous Deployment

**CI/CD Pipeline:**
1. Code push to repository
2. Run linting (pylint, eslint)
3. Run security scan (bandit)
4. Run unit tests (pytest)
5. Run integration tests
6. Build frontend assets
7. Create deployment package
8. Deploy to staging/production

---

## Performance Considerations

### Backend Optimizations

1. **Database Indexing** - Primary keys and foreign keys indexed
2. **Connection Pooling** - Reuse database connections
3. **Query Optimization** - Minimize N+1 queries
4. **Rate Limiting** - Prevent resource exhaustion
5. **Error Handling** - Graceful degradation

### Frontend Optimizations

1. **Code Splitting** - React lazy loading (future enhancement)
2. **Memoization** - useCallback for function references
3. **Conditional Rendering** - Only render necessary components
4. **Debouncing** - Form input optimization (future enhancement)
5. **Image Optimization** - CSS-only UI, minimal assets

### Scalability Considerations

**Current Limitations:**
- SQLite suitable for low-to-medium concurrent users
- In-memory rate limiter resets on restart
- No horizontal scaling support

**Future Enhancements:**
- Migrate to PostgreSQL for higher concurrency
- Implement Redis for distributed rate limiting
- Add caching layer (Redis/Memcached)
- Implement background job processing
- Add load balancing for multiple backend instances

---

## Monitoring and Logging

### Application Logging

**Backend Logging:**
- Startup/shutdown events
- Database initialization
- Error conditions with stack traces
- Security events (failed logins, lockouts)
- Performance metrics (future enhancement)

**Frontend Logging:**
- Console errors for development
- Error boundary for production (future enhancement)
- User action tracking (future enhancement)

### Health Monitoring

**Endpoints:**
- `GET /` - Root endpoint with version info
- `GET /health` - Health check endpoint

**Monitoring Metrics:**
- Response time
- Error rate
- Request volume
- Database connection status

---

## Disaster Recovery

### Backup Strategy

**Database Backups:**
- Regular SQLite file backups
- Automated daily backups recommended
- Version-controlled migrations
- Point-in-time recovery capability

**Code Backups:**
- Git version control
- Remote repository (GitHub)
- Tagged releases
- Documentation versioning

### Recovery Procedures

1. **Database Corruption:**
   - Restore from latest backup
   - Re-run migrations if needed
   - Verify data integrity

2. **Code Deployment Failure:**
   - Rollback to previous version
   - Check error logs
   - Fix issues and redeploy

3. **Data Loss:**
   - Restore from backup
   - Notify affected users
   - Investigate root cause

---

## Conclusion

This architecture provides a solid foundation for the Helping Hands volunteer management system. The modular design allows for easy maintenance and future enhancements, while the clear separation of concerns ensures each component can evolve independently.

**Key Strengths:**
- Clean separation of frontend and backend
- RESTful API design for flexibility
- Comprehensive security controls
- Automated database migrations
- Extensive test coverage
- Well-documented codebase

**Future Architecture Considerations:**
- Microservices decomposition for larger scale
- Event-driven architecture for real-time updates
- API gateway for enhanced routing and security
- Containerization for consistent deployment
- Cloud-native architecture for scalability

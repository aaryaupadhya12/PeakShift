# API Documentation

Base URL: `http://localhost:8000/api`

## Authentication Endpoints

### POST /auth/login
Login with username and password.

**Request:**
```json
{"username": "volunteer", "password": "volunteer123"}
```

**Response (200):**
```json
{"username": "volunteer", "role": "volunteer", "message": "Login successful"}
```

### POST /auth/generate-otp
Generate OTP for admin users. Query parameter: `username`

**Response (200):**
```json
{"requires_otp": true, "otp": "123456", "expires_in": "5 minutes"}
```

### POST /auth/verify-otp
Verify OTP code.

**Request:**
```json
{"username": "admin", "otp": "123456"}
```

**Response (200):**
```json
{"verified": true, "message": "OTP verified successfully"}
```

## Account Lockout Endpoints

### GET /auth/check-lockout/{username}
Check if account is locked.

**Response (200):**
```json
{"locked": false, "attempts": 0, "message": "Account is active"}
```

### POST /auth/record-failed-attempt
Record failed login. Query parameter: `username`

**Response (200):**
```json
{"locked": false, "attempts": 1, "remaining_attempts": 2, "message": "Failed attempt recorded. 2 attempts remaining"}
```

### POST /auth/reset-attempts
Reset login attempts. Query parameter: `username`

**Response (200):**
```json
{"success": true, "message": "Login attempts reset successfully"}
```

## RBAC Endpoints

### GET /rbac/roles/{role}/permissions
Get permissions for a role (admin, manager, volunteer).

**Response (200):**
```json
{"role": "manager", "permissions": ["create_shift", "publish_shift", "delete_shift", "view_all_shifts", "volunteer_for_shift"]}
```

### GET /rbac/check-permission
Check user permission. Query parameters: `username`, `action`

**Response (200):**
```json
{"username": "manager", "role": "manager", "action": "create_shift", "has_permission": true, "message": "Permission granted"}
```

### POST /rbac/validate-action
Validate user action. Query parameters: `username`, `role`, `action`

**Response (200):**
```json
{"valid": true, "username": "admin", "role": "admin", "action": "manage_users", "message": "Action authorized"}
```

## Shift Management Endpoints

### POST /shifts
Create a new shift (managers only). Query parameter: `created_by`

**Request:**
```json
{
  "title": "Morning Shift",
  "date": "2025-11-15",
  "start_time": "09:00",
  "end_time": "13:00",
  "spots": 5
}
```

**Response (200):**
```json
{"id": 1, "status": "draft", "message": "Shift created, awaiting admin validation"}
```

### POST /shifts/{shift_id}/validate
Validate a shift (admins only). Query parameter: `validated_by`

**Response (200):**
```json
{"id": 1, "status": "validated", "validated_by": "admin"}
```

### POST /shifts/{shift_id}/publish
Publish a validated shift (managers only). Query parameter: `published_by`

**Response (200):**
```json
{"id": 1, "status": "published", "published_by": "manager"}
```

### DELETE /shifts/{shift_id}
Cancel a shift (managers/admins only). Query parameters: `cancelled_by`, `role`

**Response (200):**
```json
{"message": "Shift cancelled"}
```

### GET /shifts
Get all shifts. Optional query parameter: `status` (draft, validated, published)

**Response (200):**
```json
[
  {
    "id": 1,
    "title": "Morning Shift",
    "date": "2025-11-15",
    "start_time": "09:00",
    "end_time": "13:00",
    "spots": 5,
    "status": "published",
    "created_by": "manager"
  }
]
```

### POST /shifts/{shift_id}/volunteer
Volunteer signs up for a shift. Query parameter: `username`

**Response (200):**
```json
{
  "commitment_id": 1,
  "status": "pending",
  "message": "Signed up successfully, awaiting manager approval"
}
```

**Response (overlap detected):**
```json
{
  "status": "overlap",
  "message": "You have an overlapping shift commitment",
  "alternative_shifts": [
    {
      "id": 3,
      "title": "Alternative Shift",
      "date": "2025-11-16",
      "start_time": "14:00",
      "end_time": "18:00"
    }
  ]
}
```

### POST /volunteer-commitments/{commitment_id}/approve
Manager approves or rejects volunteer commitment. Query parameter: `manager_username`

**Request:**
```json
{
  "volunteer_commitment_id": 1,
  "approved": true
}
```

**Response (200):**
```json
{
  "status": "approved",
  "message": "Volunteer approved successfully",
  "can_cancel_until": "2025-11-15T21:00:00"
}
```

**Features:**
- Decrements available spots when approved
- Increments volunteer credits (for preferential selection)
- Sets 12-hour cancellation window
- Can reject with `"approved": false`

### POST /volunteer-commitments/{commitment_id}/cancel
Volunteer cancels their approved commitment within the allowed window. Query parameter: `username`

**Response (200):**
```json
{
  "status": "cancelled",
  "message": "Volunteer commitment cancelled successfully"
}
```

**Features:**
- Only allowed within 12-hour window after approval
- Restores available spot to shift
- Commitment status changed to 'cancelled'

### GET /volunteer-commitments
Get volunteer commitments. Optional query parameters: `username`, `shift_id`, `status`

**Response (200):**
```json
[
  {
    "id": 1,
    "username": "volunteer",
    "shift_id": 1,
    "volunteered_at": "2025-11-15T09:00:00",
    "status": "approved",
    "approved_at": "2025-11-15T09:30:00",
    "approved_by": "manager",
    "can_cancel_until": "2025-11-15T21:30:00"
  }
]
```

## Manager Coverage Report Endpoints

### POST /reports/coverage
Generate a coverage report for managers showing shift fill status and participation rates.

**Request:**
```json
{
  "shifts": [
    {
      "id": "s1",
      "date": "2025-11-01",
      "location": "Store A",
      "required_staff": 2,
      "assigned_staff": ["user1", "user2"]
    }
  ],
  "start_date": "2025-11-01",
  "end_date": "2025-11-30",
  "location": "Store A"
}
```

**Response (200):**
```json
{
  "shifts": [
    {
      "id": "s1",
      "date": "2025-11-01",
      "location": "Store A",
      "required_staff": 2,
      "assigned_count": 2,
      "filled": true
    }
  ],
  "participation": {
    "user1": {
      "assigned": 5,
      "rate": 0.5
    },
    "user2": {
      "assigned": 3,
      "rate": 0.3
    }
  },
  "total_shifts": 10,
  "filters": {
    "start_date": "2025-11-01",
    "end_date": "2025-11-30",
    "location": "Store A"
  }
}
```

### POST /reports/coverage/export
Export coverage report to CSV format.

**Request:** Same as /reports/coverage

**Response (200):**
```csv
id,date,location,required_staff,assigned_count,filled
s1,2025-11-01,Store A,2,2,True

staff_id,assigned,rate
user1,5,0.5000
user2,3,0.3000
```

**Features:**
- Filter by date range (start_date, end_date)
- Filter by location
- Shows fill status per shift (filled/unfilled)
- Calculates participation rate per staff member
- Exportable to CSV

## Shift Workflow
1. **Manager creates shift** → Status: `draft`
2. **Admin validates shift** → Status: `validated`
3. **Manager publishes shift** → Status: `published`
4. **Volunteers can sign up** (when published)
5. **Manager/Admin can cancel** (delete shift)

## Error Codes
- 200: Success
- 400: Bad Request
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 500: Internal Server Error
# User Guide

## Accessing the System
Open browser and navigate to: `http://localhost:3000`

## Login Process

### Volunteer/Manager Login
1. Enter username and password
2. Click "Login"
3. Success screen displays with shift dashboard

### Admin Login (Two-Factor Authentication)
1. Enter username: `admin` and password: `admin123`
2. Click "Login"
3. Copy the 6-digit OTP displayed on screen
4. Enter OTP in the input field
5. Click "Verify OTP"
6. Success screen displays with shift dashboard

## Default Credentials

| Role | Username | Password | 2FA Required |
|------|----------|----------|--------------|
| Admin | admin | admin123 | Yes |
| Manager | manager | manager123 | No |
| Volunteer | volunteer | volunteer123 | No |

## Account Security
- Maximum 3 failed login attempts
- Account locks for 15 minutes after 3 failures
- OTP expires after 5 minutes for admin users
- Passwords are securely hashed in the database

## User Roles & Permissions

### Volunteer
- View all published shifts
- Sign up for available shifts
- Cancel own shift commitments
- View own volunteered shifts

### Manager
- All volunteer permissions, plus:
- Create new shifts (starts in "draft" status)
- Publish validated shifts
- Delete/cancel shifts
- View shifts in all statuses (draft, validated, published)
- **Generate coverage reports** to track staffing effectiveness
- **View participation rates** by staff member
- **Export reports to CSV** for analysis

### Admin
- All manager permissions, plus:
- Validate draft shifts created by managers
- Manage user accounts
- Override shift operations
- Full system access

## Shift Management

### Shift Workflow
1. **Draft** → Manager creates shift
2. **Validated** → Admin validates shift
3. **Published** → Manager publishes shift (volunteers can now sign up)

### For Managers: Creating a Shift
1. Log in with manager credentials
2. Navigate to "Create Shift" section
3. Enter shift details:
   - Title (e.g., "Weekend Food Drive")
   - Date (YYYY-MM-DD format)
   - Start time (HH:MM format)
   - End time (HH:MM format)
   - Number of spots available
4. Click "Create Shift"
5. Shift is created with "draft" status
6. Wait for admin validation before publishing

### For Admins: Validating Shifts
1. Log in with admin credentials
2. View all shifts in "draft" status
3. Review shift details
4. Click "Validate Shift" to approve
5. Shift status changes to "validated"
6. Manager can now publish the shift

### For Managers: Publishing Shifts
1. View validated shifts
2. Click "Publish Shift"
3. Shift becomes visible to all volunteers
4. Volunteers can now sign up

### For Volunteers: Signing Up for Shifts
1. Log in with volunteer credentials
2. Browse published shifts
3. Check available spots
4. Click "Sign Up" for desired shift
5. **Wait for manager approval** (commitment status: "pending")
6. Once approved, you'll receive confirmation
7. **Note your cancellation window** (12 hours from approval)
8. View your commitments in "My Shifts"

**Overlapping Shifts Protection:**
- System automatically checks for time conflicts
- If you're already committed to a shift at the same time
- You'll see alternative shift suggestions instead
- Prevents double-booking

**Credits System:**
- Earn 1 credit per approved shift
- Credits visible in your profile
- Managers may prioritize volunteers with higher credits

### For Managers: Approving Volunteers
1. Log in with manager credentials
2. Navigate to "Pending Commitments"
3. Review volunteer signup requests
4. Check volunteer's credit history (optional)
5. Click "Approve" or "Reject"
6. On approval:
   - Volunteer gets 12-hour cancellation window
   - Available spots decrease by 1
   - Volunteer earns 1 credit

### For Volunteers: Cancelling Your Commitment
1. View your approved commitments
2. Check cancellation deadline (12 hours from approval)
3. Click "Cancel Commitment" if within window
4. Spot becomes available again
5. **After deadline**: Cannot cancel, must contact manager

### Cancelling Shifts
- **Managers/Admins**: Can delete any shift at any status
- **Volunteers**: Can cancel their own commitments
- Cancelled shifts are removed from the system
- Volunteers on cancelled shifts are notified

## Manager Coverage Reports

### Generating Reports (Managers Only)
1. Log in with manager credentials
2. Navigate to "Coverage Reports" section
3. Select filter options:
   - **Date Range**: Start and end dates (optional)
   - **Location**: Filter by specific store/location (optional)
4. Click "Generate Report"
5. View report showing:
   - All shifts with fill status (filled/unfilled)
   - Number of assigned staff vs. required staff
   - Participation rate by staff member

### Understanding the Report

**Shift Fill Status**
- **Filled**: Shift has enough staff assigned (assigned ≥ required)
- **Unfilled**: Shift needs more staff (assigned < required)
- Shows required staff count vs. actual assigned count

**Participation Rates**
- Displays each staff member's participation
- Shows number of shifts assigned to each person
- Calculates participation rate (% of total shifts)
- Helps identify highly engaged staff members

### Exporting to CSV
1. Generate a coverage report
2. Click "Export to CSV" button
3. CSV file downloads with two sections:
   - **Shifts**: id, date, location, required_staff, assigned_count, filled
   - **Participation**: staff_id, assigned, rate
4. Open in Excel or similar for further analysis

### Use Cases
- **Track staffing effectiveness**: See which shifts are consistently filled
- **Identify gaps**: Find shifts that need more volunteers
- **Recognize contributors**: See which staff members participate most
- **Plan ahead**: Use historical data for future scheduling
- **Report to management**: Export professional CSV reports

## Dashboard Features

### Shift Cards Display
- **Title**: Name of the shift
- **Date & Time**: When the shift occurs
- **Status**: Current workflow status (draft/validated/published)
- **Available Spots**: How many volunteers can sign up
- **Created By**: Which manager created it

### Commitment Status Indicators
When you view "My Shifts", you'll see status indicators:
- **Pending**: Awaiting manager approval
- **Approved**: Manager approved, you're committed to this shift
- **Rejected**: Manager declined your signup
- **Cancelled**: You cancelled within the allowed window

**Approved Commitments Show:**
- Cancellation deadline (12 hours from approval time)
- Manager who approved you
- Shift details and location

### Filtering Shifts
- View all shifts
- Filter by status (draft, validated, published)
- Search by date
- View only your commitments (volunteers)

## Troubleshooting

### Login Issues

**Invalid credentials**
- Check username and password spelling
- Verify Caps Lock is off
- Ensure you're using the correct role credentials

**Account locked**
- Wait 15 minutes for automatic unlock
- Account unlocks automatically after lockout period
- Contact admin if lockout persists

**Invalid OTP (Admin users)**
- Login again to generate new OTP
- Enter OTP code within 5 minutes
- Copy OTP exactly as displayed
- No spaces before/after the code

### Shift Management Issues

**Cannot create shift (Managers)**
- Verify you're logged in as manager
- Check all required fields are filled
- Ensure date format is correct (YYYY-MM-DD)
- Ensure time format is correct (HH:MM)

**Cannot validate shift (Admins)**
- Verify you're logged in as admin with verified OTP
- Ensure shift is in "draft" status
- Refresh page if shift doesn't appear

**Cannot publish shift (Managers)**
- Ensure shift is in "validated" status
- Only validated shifts can be published
- Wait for admin validation first

**Cannot sign up for shift (Volunteers)**
- Ensure shift is in "published" status
- Check if spots are still available
- Verify you haven't already signed up
- **Check for overlapping shifts** - you may have a conflict
- **Check if previously rejected** - cannot re-signup after rejection
- Refresh page to see current availability

### System Issues

**Server error**
- Check if backend server is running on port 8000
- Verify frontend is running on port 3000
- Contact system administrator
- Check browser console for error details

**Page not loading**
- Refresh the browser
- Clear browser cache
- Check internet connection
- Verify correct URL (http://localhost:3000)

**Dashboard not showing shifts**
- Refresh the page
- Check if any shifts exist in the system
- Verify your role permissions
- Try logging out and back in

## Logout
Click the "Logout" button in the top right to:
- End your current session
- Return to login screen
- Clear any temporary data
- Require re-authentication for next access

## Best Practices

### For Volunteers
- Sign up for shifts you can commit to
- **Respond to approval notifications promptly**
- **Note your cancellation deadline** (12 hours from approval)
- Cancel well in advance if unable to attend (within window)
- Check shift details carefully before signing up
- Keep track of your committed shifts
- **Build your credits** by completing approved shifts

### For Managers
- Create shifts well in advance
- Provide clear, descriptive titles
- Set realistic spot numbers
- Wait for admin validation before publishing
- Monitor volunteer sign-ups regularly
- **Review volunteer requests promptly** (check pending commitments)
- **Consider volunteer credit history** when approving
- **Approve or reject volunteers** within reasonable time

### For Admins
- Review draft shifts promptly
- Validate shifts only after careful review
- Monitor system security alerts
- Respond to user access issues quickly

### For Volunteers
- Sign up for shifts you can commit to
- Cancel well in advance if unable to attend
- Check shift details carefully before signing up
- Keep track of your committed shifts

## Support
If you experience issues not covered in this guide:
- Contact your team's Scrum Master
- Reach out to Teaching Assistants
- Consult the API documentation for technical details
- Check the Developer Guide for system architecture
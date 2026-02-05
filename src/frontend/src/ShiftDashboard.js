import React, { useState, useEffect, useCallback } from 'react';
import './ShiftDashboard.css';

function ShiftDashboard({ user, api, onLogout }) {
  const [shifts, setShifts] = useState([]);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [newShift, setNewShift] = useState({
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    spots: '',
    location: ''
  });
  const [volunteerCommitments, setVolunteerCommitments] = useState([]);
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [alternativeShifts, setAlternativeShifts] = useState([]);
  const [showCoverageReport, setShowCoverageReport] = useState(false);
  const [coverageReport, setCoverageReport] = useState(null);
  const [reportFilters, setReportFilters] = useState({
    start_date: '',
    end_date: '',
    location: ''
  });

  const fetchShifts = useCallback(async () => {
    try {
      const res = await fetch(`${api}/shifts?user_role=${user.role}`);
      if (res.ok) {
        const data = await res.json();
        setShifts(data);
      }
    } catch (err) {
      setMessage({ text: 'Failed to load shifts', type: 'error' });
    }
  }, [api, user.role]);

  const fetchCommitments = useCallback(async () => {
    if (user.role === 'volunteer') {
      try {
        const res = await fetch(`${api}/volunteer-commitments?username=${user.username}`);
        if (res.ok) {
          const data = await res.json();
          setVolunteerCommitments(data);
        }
      } catch (err) {
        setMessage({ text: 'Failed to load commitments', type: 'error' });
      }
    }
  }, [api, user]);

  useEffect(() => {
    fetchShifts();
    fetchCommitments();
  }, [fetchShifts, fetchCommitments]);

  const handleValidate = async (shiftId) => {
    try {
      const res = await fetch(`${api}/shifts/${shiftId}/validate?validated_by=${user.username}`, { method: 'POST' });
      if (res.ok) {
        setMessage({ text: 'Shift validated', type: 'success' });
        fetchShifts();
      }
    } catch (err) {
      setMessage({ text: 'Validation failed', type: 'error' });
    }
  };

  const handlePublish = async (shiftId) => {
    try {
      const res = await fetch(`${api}/shifts/${shiftId}/publish?published_by=${user.username}`, { method: 'POST' });
      if (res.ok) {
        setMessage({ text: 'Shift published', type: 'success' });
        fetchShifts();
      }
    } catch (err) {
      setMessage({ text: 'Publish failed', type: 'error' });
    }
  };

  const handleCancel = async (shiftId) => {
    try {
      const res = await fetch(`${api}/shifts/${shiftId}?cancelled_by=${user.username}&role=${user.role}`, { method: 'DELETE' });
      if (res.ok) {
        setMessage({ text: 'Shift cancelled', type: 'success' });
        fetchShifts();
      }
    } catch (err) {
      setMessage({ text: 'Cancel failed', type: 'error' });
    }
  };

  const handleVolunteerSignup = async (shiftId) => {
    try {
      const res = await fetch(`${api}/shifts/${shiftId}/volunteer?username=${user.username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await res.json();
      
      if (res.ok) {
        if (data.status === 'pending') {
          setMessage({ text: data.message, type: 'success' });
          fetchCommitments();
          fetchShifts(); // Refresh shifts to update available spots
        } else if (data.status === 'overlap') {
          setMessage({ text: data.message, type: 'warning' });
          setAlternativeShifts(data.alternative_shifts);
          setShowAlternatives(true);
        }
      } else {
        let errorMessage = 'Failed to sign up';
        if (data.detail) {
          errorMessage = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        }
        setMessage({ text: errorMessage, type: 'error' });
      }
    } catch (err) {
      console.error('Signup error:', err);
      setMessage({ text: 'Failed to sign up. Please try again.', type: 'error' });
    }
  };

  const handleApproveVolunteer = async (commitmentId, approved) => {
    try {
      const res = await fetch(`${api}/volunteer-commitments/${commitmentId}/approve?manager_username=${user.username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          volunteer_commitment_id: commitmentId,
          approved: approved
        })
      });

      const data = await res.json();
      
      if (res.ok) {
        setMessage({ text: data.message, type: 'success' });
        fetchShifts();
        fetchCommitments();
      } else {
        setMessage({ text: data.detail || 'Failed to process approval', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Failed to process approval', type: 'error' });
    }
  };

  const handleVolunteerCancel = async (commitmentId) => {
    try {
      const res = await fetch(`${api}/volunteer-commitments/${commitmentId}/cancel?username=${user.username}`, {
        method: 'POST'
      });

      const data = await res.json();
      
      if (res.ok) {
        setMessage({ text: data.message, type: 'success' });
        fetchShifts();
        fetchCommitments();
      } else {
        setMessage({ text: data.detail || 'Failed to cancel commitment', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Failed to cancel commitment', type: 'error' });
    }
  };

  const handleCreateShift = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${api}/shifts?created_by=${user.username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newShift)
      });
      if (res.ok) {
        setMessage({ text: 'Shift created successfully', type: 'success' });
        setNewShift({ title: '', date: '', start_time: '', end_time: '', spots: '', location: '' });
        fetchShifts();
      } else {
        const error = await res.json();
        setMessage({ text: error.detail || 'Failed to create shift', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Failed to create shift', type: 'error' });
    }
  };

  const handleGenerateCoverageReport = async () => {
    try {
      const res = await fetch(`${api}/reports/coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportFilters)
      });
      
      if (res.ok) {
        const data = await res.json();
        setCoverageReport(data);
        setShowCoverageReport(true);
        setMessage({ text: 'Coverage report generated', type: 'success' });
      } else {
        setMessage({ text: 'Failed to generate report', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Failed to generate report', type: 'error' });
    }
  };

  const handleExportCoverageReport = async () => {
    try {
      const res = await fetch(`${api}/reports/coverage/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reportFilters)
      });
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'coverage_report.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        setMessage({ text: 'Report exported successfully', type: 'success' });
      } else {
        setMessage({ text: 'Failed to export report', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Failed to export report', type: 'error' });
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Shift Dashboard - {user.role}</h2>
        <button onClick={onLogout}>Logout</button>
      </div>
      
      {message.text && (
        <div className={`message ${message.type}`}>
          {typeof message.text === 'object' ? JSON.stringify(message.text) : message.text}
        </div>
      )}
      
      {/* Show create shift form only for managers */}
      {user.role === 'manager' && (
        <div className="create-shift">
          <h3>Create New Shift</h3>
          <form onSubmit={handleCreateShift}>
            <input
              type="text"
              placeholder="Shift Title"
              value={newShift.title}
              onChange={e => setNewShift({...newShift, title: e.target.value})}
              required
            />
            <input
              type="date"
              value={newShift.date}
              onChange={e => setNewShift({...newShift, date: e.target.value})}
              required
            />
            <input
              type="time"
              value={newShift.start_time}
              onChange={e => setNewShift({...newShift, start_time: e.target.value})}
              required
            />
            <input
              type="time"
              value={newShift.end_time}
              onChange={e => setNewShift({...newShift, end_time: e.target.value})}
              required
            />
            <input
              type="number"
              placeholder="Number of Spots"
              value={newShift.spots}
              onChange={e => setNewShift({...newShift, spots: e.target.value})}
              required
            />
            <input
              type="text"
              placeholder="Location (e.g., Store A)"
              value={newShift.location}
              onChange={e => setNewShift({...newShift, location: e.target.value})}
              required
            />
            <button type="submit">Create Shift</button>
          </form>
        </div>
      )}
      
      {/* Manager Coverage Report */}
      {user.role === 'manager' && (
        <div className="coverage-report-section">
          <h3>Coverage Report</h3>
          <div className="report-filters">
            <input
              type="date"
              placeholder="Start Date"
              value={reportFilters.start_date}
              onChange={e => setReportFilters({...reportFilters, start_date: e.target.value})}
            />
            <input
              type="date"
              placeholder="End Date"
              value={reportFilters.end_date}
              onChange={e => setReportFilters({...reportFilters, end_date: e.target.value})}
            />
            <input
              type="text"
              placeholder="Location (optional)"
              value={reportFilters.location}
              onChange={e => setReportFilters({...reportFilters, location: e.target.value})}
            />
            <button onClick={handleGenerateCoverageReport}>Generate Report</button>
            {coverageReport && (
              <button onClick={handleExportCoverageReport}>Export to CSV</button>
            )}
          </div>
          
          {showCoverageReport && coverageReport && (
            <div className="coverage-report">
              <h4>Report Summary</h4>
              <p><strong>Total Shifts:</strong> {coverageReport.total_shifts}</p>
              
              <h4>Shift Fill Status</h4>
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Shift</th>
                    <th>Date</th>
                    <th>Location</th>
                    <th>Required</th>
                    <th>Assigned</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {coverageReport.shifts.map(shift => (
                    <tr key={shift.id}>
                      <td>{shift.title || shift.id}</td>
                      <td>{shift.date}</td>
                      <td>{shift.location}</td>
                      <td>{shift.required_staff}</td>
                      <td>{shift.assigned_count}</td>
                      <td className={shift.filled ? 'filled' : 'unfilled'}>
                        {shift.filled ? 'Filled' : 'Unfilled'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              <h4>Participation Rates</h4>
              <table className="report-table">
                <thead>
                  <tr>
                    <th>Staff Member</th>
                    <th>Shifts Assigned</th>
                    <th>Participation Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(coverageReport.participation).map(([staffId, stats]) => (
                    <tr key={staffId}>
                      <td>{staffId}</td>
                      <td>{stats.assigned}</td>
                      <td>{(stats.rate * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              <button onClick={() => setShowCoverageReport(false)}>Close Report</button>
            </div>
          )}
        </div>
      )}
      
      <div className="shifts">
        {user.role === 'volunteer' && (
          <div className="my-commitments">
            <h3>My Commitments</h3>
            {volunteerCommitments.map(commitment => (
              <div key={commitment.id} className="commitment-card">
                <h4>{commitment.shift_title}</h4>
                <p>{commitment.date} | {commitment.start_time} - {commitment.end_time}</p>
                <span className={`status ${commitment.status}`}>{commitment.status}</span>
                {commitment.status === 'approved' && commitment.can_cancel_until && (
                  <button
                    onClick={() => handleVolunteerCancel(commitment.id)}
                    title={`Can cancel until ${new Date(commitment.can_cancel_until).toLocaleString()}`}
                  >
                    Cancel
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <h3>Available Shifts</h3>
        {showAlternatives && (
          <div className="alternative-shifts">
            <h4>Alternative Shifts Available</h4>
            {alternativeShifts.map(shift => (
              <div key={shift.id} className="shift-card alternative">
                <h3>{shift.title}</h3>
                <p>{shift.date} | {shift.start_time} - {shift.end_time}</p>
                <p>Available Spots: {shift.spots}</p>
                <button onClick={() => {
                  handleVolunteerSignup(shift.id);
                  setShowAlternatives(false);
                }}>Sign Up</button>
              </div>
            ))}
            <button onClick={() => setShowAlternatives(false)}>Close</button>
          </div>
        )}

        {shifts.map(shift => (
          <div key={shift.id} className="shift-card">
            <h3>{shift.title}</h3>
            <p>{shift.date} | {shift.start_time} - {shift.end_time}</p>
            {shift.location && <p><strong>Location:</strong> {shift.location}</p>}
            <p>Available Spots: {shift.spots}</p>
            <span className={`status ${shift.status}`}>{shift.status}</span>
            
            {/* Admin controls */}
            {user.role === 'admin' && shift.status === 'draft' && (
              <button onClick={() => handleValidate(shift.id)}>Validate</button>
            )}
            
            {/* Manager controls */}
            {user.role === 'manager' && (
              <>
                {shift.status === 'validated' && (
                  <button onClick={() => handlePublish(shift.id)}>Publish</button>
                )}
                {shift.pending_volunteers && shift.pending_volunteers.map(volunteer => (
                  <div key={volunteer.commitment_id} className="volunteer-approval">
                    <span>{volunteer.username}</span>
                    <button onClick={() => handleApproveVolunteer(volunteer.commitment_id, true)}>
                      Approve
                    </button>
                    <button onClick={() => handleApproveVolunteer(volunteer.commitment_id, false)}>
                      Reject
                    </button>
                  </div>
                ))}
              </>
            )}
            
            {/* Cancel button for admin and manager */}
            {(user.role === 'admin' || user.role === 'manager') && (
              <button className="cancel" onClick={() => handleCancel(shift.id)}>Cancel</button>
            )}

            {/* Volunteer view */}
            {user.role === 'volunteer' && shift.status === 'published' && (
              <>
                {shift.spots > 0 ? (
                  // Check if already signed up for this shift
                  volunteerCommitments.some(c => c.shift_id === shift.id && c.status !== 'cancelled') ? (
                    <span className="already-signed-up">✓ Already signed up</span>
                  ) : (
                    <button onClick={() => handleVolunteerSignup(shift.id)}>Sign Up</button>
                  )
                ) : (
                  <span className="no-spots">No spots available</span>
                )}
              </>
            )}
          </div>
        ))}
        {shifts.length === 0 && (
          <p>No shifts available at the moment.</p>
        )}
      </div>
    </div>
  );
}

export default ShiftDashboard;
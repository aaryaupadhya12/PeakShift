import React, { useState } from 'react';
import './App.css';
import ShiftDashboard from './ShiftDashboard';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [showOtp, setShowOtp] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [user, setUser] = useState(null);

  const showMessage = (text, type) => setMessage({ text, type });
  
  // Removed unused handleApiError to fix ESLint error

  const handleLogin = async (e) => {
    e.preventDefault();
    
    // Check if account is locked first
    try {
      const lockoutRes = await fetch(`${API}/auth/check-lockout/${username}`);
      if (lockoutRes.ok) {
        const lockoutData = await lockoutRes.json();
        if (lockoutData.locked) {
          showMessage(`Account locked! ${lockoutData.message}`, 'error');
          return;
        }
      }
    } catch (err) {
      console.log('Lockout check failed, continuing...');
    }

    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (res.ok) {
        const data = await res.json();
        
        // Reset failed attempts on successful login
        await fetch(`${API}/auth/reset-attempts?username=${username}`, { method: 'POST' });
        
        if (data.role === 'admin') {
          const otpRes = await fetch(`${API}/auth/generate-otp?username=${username}`, { method: 'POST' });
          const otpData = await otpRes.json();
          setShowOtp(true);
          setUser(data);
          showMessage(`OTP Generated: ${otpData.otp} (expires in 5 min)`, 'info');
        } else {
          setUser(data);
          showMessage('Login successful!', 'success');
        }
      } else {
        // Record failed attempt
        const failRes = await fetch(`${API}/auth/record-failed-attempt?username=${username}`, { method: 'POST' });
        if (failRes.ok) {
          const failData = await failRes.json();
          if (failData.locked) {
            showMessage(`Account locked for 15 minutes! Too many failed attempts.`, 'error');
          } else {
            showMessage(`Invalid credentials. ${failData.remaining_attempts} attempts remaining.`, 'error');
          }
        } else {
          showMessage('Invalid credentials', 'error');
        }
      }
    } catch (err) {
      showMessage('Server error. Is backend running on port 8000?', 'error');
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, otp })
      });

      if (res.ok) {
        showMessage('OTP verified! Login successful!', 'success');
        setShowOtp(false);
      } else {
        showMessage('Invalid or expired OTP', 'error');
      }
    } catch (err) {
      showMessage('OTP verification failed', 'error');
    }
  };

  const handleLogout = () => {
    setUser(null);
    setShowOtp(false);
    setOtp('');
    setMessage({ text: '', type: '' });
  };

  return (
    <div className="App">
      <div className="container">
        <h1>🤝 Helping Hands</h1>
        <p className="subtitle">Volunteer Management System</p>

        {message.text && (
          <div className={`message ${message.type}`}>{message.text}</div>
        )}

        {!user && !showOtp && (
          <form onSubmit={handleLogin}>
            <input type="text" placeholder="Username" value={username} 
              onChange={(e) => setUsername(e.target.value)} required />
            <input type="password" placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit">Login</button>
          </form>
        )}

        {showOtp && (
          <form onSubmit={handleVerifyOtp}>
            <input type="text" placeholder="Enter 6-digit OTP" maxLength="6"
              value={otp} onChange={(e) => setOtp(e.target.value)} required />
            <button type="submit">Verify OTP</button>
          </form>
        )}

        {user && !showOtp && (
          <>
            <div className="user-info">
              <h3>Logged In</h3>
              <p><strong>User:</strong> {user.username}</p>
                <p><strong>Role:</strong> {user.role}</p>
                {/* Small UX: show volunteer credits if available (non-intrusive) */}
                {user.credits !== undefined && (
                  <p><strong>Credits:</strong> {user.credits}</p>
                )}
              <button onClick={handleLogout}>Logout</button>
            </div>
            <ShiftDashboard user={user} api={API} onLogout={handleLogout} />
          </>
        )}
      </div>
    </div>
  );
}

export default App;
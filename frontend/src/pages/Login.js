import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';
import config from '../config.js'; // Adjust the import path as needed
import { setAuthToken } from '../utils/auth';

function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isSignup, setIsSignup] = useState(false);
    const [signupName, setSignupName] = useState('');
    const [signupEmail, setSignupEmail] = useState('');
    const [signupPassword, setSignupPassword] = useState('');
    const [signupConfirm, setSignupConfirm] = useState('');
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const navigate = useNavigate(); // Hook to programmatically navigate

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const response = await fetch(`${config.API_BASE_URL}/auth/login`, 
                {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed');
            }

            // Store the token and call the onLogin handler
            setAuthToken(data.token);
            onLogin(data.token);

            // After login, check onboarding state
            try {
                const st = await fetch(`${config.API_BASE_URL}/onboarding/state`, {
                    headers: { 'Authorization': `Bearer ${data.token}` }
                });
                const stData = await st.json();
                if (st.ok && stData.onboarding_status === 'pending') {
                    navigate('/onboarding');
                } else {
                    navigate('/');
                }
            } catch(_e) {
                navigate('/');
            }
        } catch (err) {
            setError(err.message);
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setError('');
        const name = signupName.trim();
        const email = signupEmail.trim();
        const pwd = signupPassword;
        const confirm = signupConfirm;
        if (!name || !email || !pwd) {
            setError('Please fill in name, email, and password.');
            return;
        }
        if (pwd !== confirm) {
            setError('Passwords do not match.');
            return;
        }
        try {
            const response = await fetch(`${config.API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: name, email, password: pwd })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Signup failed');
            }
            setAuthToken(data.token);
            onLogin(data.token);
            // New users start with onboarding_status = pending
            navigate('/onboarding');
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="login-page">
            <div className="animated-bg" aria-hidden="true">
                <div className="orb orb-1"></div>
                <div className="orb orb-2"></div>
                <div className="orb orb-3"></div>
                <div className="bg-overlay"></div>
            </div>

            <div className="login-container login-card animate-in">
                <div className="brand">
                    <img
                        src="/logo.svg"
                        alt="Portal logo"
                        className="brand-logo"
                        onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    {isSignup ? (
                        <>
                            <h1>Create your account</h1>
                            <p className="subtitle">Join and start your journey</p>
                        </>
                    ) : (
                        <>
                            <h1>Welcome back</h1>
                            <p className="subtitle">Your learning journey continues today</p>
                        </>
                    )}
                </div>

                {isSignup ? (
                    <form onSubmit={handleSignup} noValidate>
                        <div className="form-group">
                            <label htmlFor="name">Name</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5Z" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="M21 22c0-4.418-4.03-8-9-8s-9 3.582-9 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                    </svg>
                                </span>
                                <input
                                    type="text"
                                    id="name"
                                    className="input-field"
                                    value={signupName}
                                    onChange={(e) => setSignupName(e.target.value)}
                                    placeholder="Enter your name"
                                    autoComplete="name"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M3 5h18v14H3z" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="m3 7 9 6 9-6" stroke="currentColor" strokeWidth="1.6"/>
                                    </svg>
                                </span>
                                <input
                                    type="email"
                                    id="email"
                                    className="input-field"
                                    value={signupEmail}
                                    onChange={(e) => setSignupEmail(e.target.value)}
                                    placeholder="Enter your email"
                                    autoComplete="email"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="signup-password">Password</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <rect x="3" y="10" width="18" height="11" rx="2.5" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="M7 10V8a5 5 0 0 1 10 0v2" stroke="currentColor" strokeWidth="1.6"/>
                                    </svg>
                                </span>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="signup-password"
                                    className="input-field"
                                    value={signupPassword}
                                    onChange={(e) => setSignupPassword(e.target.value)}
                                    placeholder="Create a password"
                                    autoComplete="new-password"
                                    required
                                />
                                <button
                                    type="button"
                                    className="toggle-password"
                                    onClick={() => setShowPassword((v) => !v)}
                                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                                >
                                    {showPassword ? (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M3 3l18 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                                            <path d="M10.584 10.585A3 3 0 0 0 12 15a3 3 0 0 0 3.415-1.415" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12c-.347.643-1.97 3.247-5.25 4.99" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                        </svg>
                                    ) : (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" stroke="currentColor" strokeWidth="1.6"/>
                                            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/>
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="signup-password-confirm">Confirm Password</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <rect x="3" y="10" width="18" height="11" rx="2.5" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="M7 10V8a5 5 0 0 1 10 0v2" stroke="currentColor" strokeWidth="1.6"/>
                                    </svg>
                                </span>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="signup-password-confirm"
                                    className="input-field"
                                    value={signupConfirm}
                                    onChange={(e) => setSignupConfirm(e.target.value)}
                                    placeholder="Re-enter your password"
                                    autoComplete="new-password"
                                    required
                                />
                                <button
                                    type="button"
                                    className="toggle-password"
                                    onClick={() => setShowPassword((v) => !v)}
                                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                                >
                                    {showPassword ? (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M3 3l18 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                                            <path d="M10.584 10.585A3 3 0 0 0 12 15a3 3 0 0 0 3.415-1.415" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12c-.347.643-1.97 3.247-5.25 4.99" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                        </svg>
                                    ) : (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" stroke="currentColor" strokeWidth="1.6"/>
                                            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/>
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        {error && <p className="error">{error}</p>}

                        <button type="submit" className="primary-btn">Create account</button>
                    </form>
                ) : (
                    <form onSubmit={handleSubmit} noValidate>
                        <div className="form-group">
                            <label htmlFor="username">Username</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5Z" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="M21 22c0-4.418-4.03-8-9-8s-9 3.582-9 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                    </svg>
                                </span>
                                <input
                                    type="text"
                                    id="username"
                                    className="input-field"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Enter your username"
                                    autoComplete="username"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">Password</label>
                            <div className="input-group">
                                <span className="input-icon" aria-hidden="true">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <rect x="3" y="10" width="18" height="11" rx="2.5" stroke="currentColor" strokeWidth="1.6"/>
                                        <path d="M7 10V8a5 5 0 0 1 10 0v2" stroke="currentColor" strokeWidth="1.6"/>
                                    </svg>
                                </span>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="password"
                                    className="input-field"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Enter your password"
                                    autoComplete="current-password"
                                    required
                                />
                                <button
                                    type="button"
                                    className="toggle-password"
                                    onClick={() => setShowPassword((v) => !v)}
                                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                                >
                                    {showPassword ? (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M3 3l18 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                                            <path d="M10.584 10.585A3 3 0 0 0 12 15a3 3 0 0 0 3.415-1.415" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12c-.347.643-1.97 3.247-5.25 4.99" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                                        </svg>
                                    ) : (
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" stroke="currentColor" strokeWidth="1.6"/>
                                            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6"/>
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </div>

                        {error && <p className="error">{error}</p>}

                        <button type="submit" className="primary-btn">Sign in</button>
                    </form>
                )}

                <div style={{ marginTop: 12, textAlign: 'center' }}>
                    {isSignup ? (
                        <span>
                            Already have an account?{' '}
                            <button style={{ background: 'transparent', border: 0, color: '#93c5fd', cursor: 'pointer' }} onClick={() => { setError(''); setIsSignup(false); }}>
                                Sign in
                            </button>
                        </span>
                    ) : (
                        <span>
                            Don\'t have an account?{' '}
                            <button style={{ background: 'transparent', border: 0, color: '#93c5fd', cursor: 'pointer' }} onClick={() => { setError(''); setIsSignup(true); }}>
                                Sign up
                            </button>
                        </span>
                    )}
                </div>

                <div className="oauth-section">
                    <div className="oauth-sep">or</div>
                    <div className="oauth-buttons">
                        <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/google/start`}>Continue with Google</a>
                        <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/facebook/start`}>Continue with Facebook</a>
                        <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/linkedin/start`}>Continue with LinkedIn</a>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Login;
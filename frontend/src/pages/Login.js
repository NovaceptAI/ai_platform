import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';
import config from '../config.js';
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
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const response = await fetch(`${config.API_BASE_URL}/auth/login`, {
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

            setAuthToken(data.token);
            onLogin(data.token);

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
        if (!isStrong) {
            setError('Password is not strong enough.');
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
            navigate('/onboarding');
        } catch (err) {
            setError(err.message);
        }
    };

    // Password strength checks for signup
    const pw = signupPassword || '';
    const hasMinLength = pw.length >= 8;
    const hasUpper = /[A-Z]/.test(pw);
    const hasLower = /[a-z]/.test(pw);
    const hasNumber = /[0-9]/.test(pw);
    const hasSpecial = /[^A-Za-z0-9]/.test(pw);
    const isStrong = hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial;
    const passwordsMatch = signupPassword && signupConfirm && signupPassword === signupConfirm;
    const canSubmitSignup = Boolean(
        (signupName || '').trim() && (signupEmail || '').trim() && isStrong && passwordsMatch
    );

    return (
        <div className="login-page">
            {/* Left Hero Section */}
            <div className="hero-section">
                <video
                    className="hero-video"
                    autoPlay
                    loop
                    muted
                    playsInline
                    src="/demo/hero.mp4"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
                <div className="hero-overlay"></div>
                <div className="hero-content">
                    <div className="hero-logo">Scoolish</div>
                    <h1 className="hero-title">
                        Transform how you learn,<br />
                        think, and create.
                    </h1>
                    <p className="hero-description">
                        Log in to begin your personalized Scoolish journey.
                    </p>
                </div>
            </div>

            {/* Right Form Section */}
            <div className="form-section">
                <div className="login-container login-card">
                    <div className="brand">
                        <img
                            src="/demo/scoolish_logo.svg"
                            alt="Scoolish logo"
                            className="brand-logo"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        {isSignup ? (
                            <>
                                <h1>Join Scoolish</h1>
                                <p className="subtitle">
                                    Already have an account?{' '}
                                    <button onClick={() => { setError(''); setIsSignup(false); }}>
                                        Sign in
                                    </button>
                                </p>
                            </>
                        ) : (
                            <>
                                <h1>Welcome to Scoolish</h1>
                                <p className="subtitle">
                                    Don't have an account?{' '}
                                    <button onClick={() => { setError(''); setIsSignup(true); }}>
                                        Sign up for free
                                    </button>
                                </p>
                            </>
                        )}
                    </div>

                    {isSignup ? (
                        <form onSubmit={handleSignup} noValidate>
                            {error && <p className="error">{error}</p>}

                            <div className="form-inputs-wrapper">
                                <input
                                    type="text"
                                    className="input-field"
                                    value={signupName}
                                    onChange={(e) => setSignupName(e.target.value)}
                                    placeholder="Name"
                                    autoComplete="name"
                                    required
                                />

                                <input
                                    type="email"
                                    className="input-field"
                                    value={signupEmail}
                                    onChange={(e) => setSignupEmail(e.target.value)}
                                    placeholder="Email"
                                    autoComplete="email"
                                    required
                                />

                                <div className="password-wrapper">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        className="input-field"
                                        value={signupPassword}
                                        onChange={(e) => setSignupPassword(e.target.value)}
                                        placeholder="Password"
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

                                {signupPassword && (
                                    <div className="pw-hints" aria-live="polite">
                                        <div className={`pw-hint ${hasMinLength ? 'ok' : 'bad'}`}>{hasMinLength ? '✔' : '✖'} At least 8 characters</div>
                                        <div className={`pw-hint ${hasUpper ? 'ok' : 'bad'}`}>{hasUpper ? '✔' : '✖'} Contains an uppercase letter</div>
                                        <div className={`pw-hint ${hasLower ? 'ok' : 'bad'}`}>{hasLower ? '✔' : '✖'} Contains a lowercase letter</div>
                                        <div className={`pw-hint ${hasNumber ? 'ok' : 'bad'}`}>{hasNumber ? '✔' : '✖'} Contains a number</div>
                                        <div className={`pw-hint ${hasSpecial ? 'ok' : 'bad'}`}>{hasSpecial ? '✔' : '✖'} Contains a special character</div>
                                    </div>
                                )}

                                <div className="password-wrapper">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        className="input-field"
                                        value={signupConfirm}
                                        onChange={(e) => setSignupConfirm(e.target.value)}
                                        placeholder="Confirm Password"
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

                                {signupConfirm && (
                                    <div className={`pw-hint ${passwordsMatch ? 'ok' : 'bad'}`} aria-live="polite">
                                        {passwordsMatch ? '✔ Passwords match' : '✖ Passwords do not match'}
                                    </div>
                                )}

                                <button type="submit" className="primary-btn" disabled={!canSubmitSignup}>
                                    Create account
                                </button>
                            </div>
                        </form>
                    ) : (
                        <form onSubmit={handleSubmit} noValidate>
                            {error && <p className="error">{error}</p>}

                            <div className="form-inputs-wrapper">
                                <input
                                    type="text"
                                    className="input-field"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Username or Email"
                                    autoComplete="username"
                                    required
                                />

                                <div className="password-wrapper">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        className="input-field"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Password"
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

                                <button type="submit" className="primary-btn">Log in</button>
                            </div>
                        </form>
                    )}

                    <div className="oauth-section">
                        <div className="oauth-sep">OR</div>
                        <div className="oauth-buttons">
                            <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/google/start`}>
                                Log in with Google
                            </a>
                            <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/facebook/start`}>
                                Log in with Apple
                            </a>
                            <a className="oauth-btn" href={`${config.API_BASE_URL}/auth/oauth/linkedin/start`}>
                                Use Single Sign-On (SSO)
                            </a>
                        </div>
                    </div>

                    {!isSignup && (
                        <a href="#" className="forgot-password">Forgot Password</a>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Login;

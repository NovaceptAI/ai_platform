import React, { useEffect, useMemo, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import "./Navbar.css";
import config from "../config";

export default function Navbar({ onToggleDock }) {
  const navigate = useNavigate();
  const [display, setDisplay] = useState(null);

  const links = useMemo(() => ([
    { to: "/", label: "Home" },
    { to: "/dashboard", label: "Dashboard" },
    { to: "/scoolish", label: "Scoolish" },
    { to: "/discover", label: "Discover" },
    { to: "/organize", label: "Organize" },
    { to: "/master", label: "Master" },
    { to: "/create", label: "Create" },
    { to: "/collaborate", label: "Collaborate" },
    { to: "/vault", label: "Vault" },
  ]), []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setDisplay(null); return; }
    (async () => {
      try {
        const res = await fetch(`${config.API_BASE_URL}/users/me`, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await res.json();
        if (res.ok) {
          if (data.account_type === 'learner' && data.profile_summary) setDisplay(`${data.username} • ${data.profile_summary}`);
          else if (data.account_type === 'educator' && data.profile_summary) setDisplay(`${data.username} • ${data.profile_summary}`);
          else if (data.account_type === 'professional' && data.profile_summary) setDisplay(`${data.username} • ${data.profile_summary}`);
          else if (data.account_type === 'organization' && data.profile_summary) setDisplay(data.profile_summary);
          else setDisplay(data.username);
        } else {
          setDisplay(null);
        }
      } catch(_) { setDisplay(null); }
    })();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  return (
    <header className="nv-navbar">
      <div className="nv-inner">
        <div className="nv-left" onClick={() => navigate("/")}>
          <div className="nv-logo">🧠 Scoolish</div>
        </div>

        <input id="nv-menu-toggle" type="checkbox" className="nv-toggle" />
        <label htmlFor="nv-menu-toggle" className="nv-burger" aria-label="Toggle Menu">
          <span></span><span></span><span></span>
        </label>

        <nav className="nv-links">
          {links.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => "nv-link" + (isActive ? " nv-active" : "")}
              end={link.to === "/"}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="nv-right">
          {display && <div className="nv-user-chip">{display}</div>}
          <button className="nv-logout" onClick={() => onToggleDock && onToggleDock()} title="Toggle Web Dock (Ctrl+Shift+K)">Web Dock</button>
          <button className="nv-logout" onClick={handleLogout}>Logout</button>
        </div>
      </div>
    </header>
  );
}
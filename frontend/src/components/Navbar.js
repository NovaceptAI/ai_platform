import React, { useMemo } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import "./Navbar.css";

export default function Navbar() {
  const navigate = useNavigate();

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
          <button className="nv-logout" onClick={handleLogout}>Logout</button>
        </div>
      </div>
    </header>
  );
}
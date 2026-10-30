import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "./api";
import { applyAppearance } from "./appearance";
import { Logo } from "./logo";
import { useSession } from "./session";

const NAV = [
  { to: "/today", label: "Today" },
  { to: "/plan", label: "Plan" },
  { to: "/coach", label: "Coach" },
  { to: "/diary", label: "Diary" },
  { to: "/progress", label: "Progress" },
  { to: "/settings", label: "Settings" },
] as const;

export function AppShell() {
  const { user, logout } = useSession();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api<{ appearance?: string }>("/api/profile/")
      .then((profile) => applyAppearance(profile.appearance || "light"))
      .catch(() => applyAppearance("light"));
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <button className="menu-button app-menu" type="button" aria-expanded={open} aria-controls="app-nav" onClick={() => setOpen((value) => !value)}>
        <span />
        <span />
        <span />
      </button>
      <aside id="app-nav" className={open ? "app-sidebar open" : "app-sidebar"}>
        <Link to="/" className="brand app-brand" aria-label="Swasthya home">
          <Logo />
          <strong className="brand-name">Swasthya</strong>
        </Link>
        <NavLink className="button log-meal-link" to="/coach?compose=1">
          Log a Meal
        </NavLink>
        <nav aria-label="App">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="app-account">
          <p>{user?.name}</p>
          <p className="muted">{user?.email}</p>
          <button type="button" className="ghost" onClick={() => void logout()}>
            Logout
          </button>
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

import { useEffect, useState, type ComponentType } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "./api";
import { applyAppearance } from "./appearance";
import { BookIcon, ChartIcon, ChatIcon, GearIcon, HomeIcon, ListIcon, LogoutIcon, PlusIcon } from "./icons";
import { Logo } from "./logo";
import { useSession } from "./session";

const NAV: ReadonlyArray<{ to: string; label: string; Icon: ComponentType<{ size?: number }> }> = [
  { to: "/today", label: "Today", Icon: HomeIcon },
  { to: "/plan", label: "Plan", Icon: ListIcon },
  { to: "/coach", label: "Coach", Icon: ChatIcon },
  { to: "/diary", label: "Diary", Icon: BookIcon },
  { to: "/progress", label: "Progress", Icon: ChartIcon },
  { to: "/settings", label: "Settings", Icon: GearIcon },
];

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
      <button className="menu-button app-menu" type="button" aria-expanded={open} aria-controls="app-nav" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen((value) => !value)}>
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
          <PlusIcon size={18} />
          Log a Meal
        </NavLink>
        <nav aria-label="App">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "is-active" : undefined)}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="app-account">
          <p>{user?.name}</p>
          <p className="muted">{user?.email}</p>
          <button type="button" className="app-logout" onClick={() => void logout()}>
            <LogoutIcon size={18} />
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

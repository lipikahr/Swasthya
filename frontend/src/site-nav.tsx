import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Logo } from "./logo";
import { useSession } from "./session";

const AUTH_PATHS = ["/login", "/register", "/forgot", "/reset-password"];
const EXPLORE = [
  ["#opening", "How it works"],
  ["#nutrition", "Nutrition"],
  ["#how", "Coach"],
  ["#questions", "Questions"],
] as const;

export function SiteNav() {
  const { user, ready, logout } = useSession();
  const { pathname } = useLocation();
  const onAuthPage = AUTH_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  const [open, setOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [exploreOpen, setExploreOpen] = useState(false);
  const onHome = pathname === "/";
  const navRef = useRef<HTMLElement>(null);
  const close = () => {
    setOpen(false);
    setAccountOpen(false);
    setExploreOpen(false);
  };

  useEffect(() => {
    if (!open && !accountOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, accountOpen]);

  useEffect(() => {
    if (!open) return;
    navRef.current?.querySelector<HTMLElement>("a, button")?.focus();
  }, [open]);

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/" end className="brand" aria-label="Swasthya home" onClick={close}>
          <Logo />
          <span>
            <strong className="brand-name">Swasthya</strong>
          </span>
        </NavLink>
        <p className="tagline">Better Food · Better Choices · A Healthier You</p>
        <button className="menu-button" type="button" aria-expanded={open} aria-controls="site-nav" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen((value) => !value)}>
          <span />
          <span />
          <span />
        </button>
        <nav id="site-nav" ref={navRef} className={open ? "open" : undefined} aria-label="Site">
          <NavLink to="/" end onClick={close}>Home</NavLink>
          <NavLink to="/log" onClick={close}>Log a Meal</NavLink>
          <div className="explore">
            <button className="explore-button" type="button" aria-expanded={exploreOpen} onClick={() => setExploreOpen((value) => !value)}>
              Explore
            </button>
            {exploreOpen ? (
              <div className="explore-menu">
                {EXPLORE.map(([hash, label]) => (
                  <a key={hash} href={onHome ? hash : `/${hash}`} onClick={close}>{label}</a>
                ))}
              </div>
            ) : null}
          </div>
          {ready && user ? (
            <div className="account">
              <button className="account-button" type="button" aria-expanded={accountOpen} onClick={() => setAccountOpen((value) => !value)}>
                {user.name}
              </button>
              {accountOpen && (
                <div className="account-menu">
                  <NavLink to="/today" onClick={() => { setAccountOpen(false); close(); }}>Today</NavLink>
                  <NavLink to="/settings" onClick={() => { setAccountOpen(false); close(); }}>Settings</NavLink>
                  <button
                    type="button"
                    className="account-logout"
                    onClick={() => {
                      setAccountOpen(false);
                      close();
                      void logout();
                    }}
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          ) : ready ? (
            <NavLink to="/login" className={onAuthPage ? "button active" : "button"} onClick={close}>
              Login / Sign Up
            </NavLink>
          ) : null}
        </nav>
      </div>
    </header>
  );
}

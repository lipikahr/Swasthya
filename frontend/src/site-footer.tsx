import { Link, NavLink, useLocation } from "react-router-dom";
import { Logo } from "./logo";

const AUTH_PATHS = ["/login", "/register", "/forgot", "/reset-password"];

const NAV_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/log", label: "Log a Meal" },
  { to: "/progress", label: "Progress" },
  { to: "/settings", label: "Settings" },
] as const;

export function SiteFooter() {
  const { pathname } = useLocation();
  const compact = pathname === "/log" || AUTH_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  const year = new Date().getFullYear();

  if (compact) {
    return (
      <footer className="site-footer is-compact">
        <div className="site-footer-inner">
          <p>© {year} Swasthya. All rights reserved.</p>
          <p>Built for healthier everyday choices.</p>
        </div>
      </footer>
    );
  }

  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-grid">
          <section className="site-footer-brand" aria-labelledby="footer-brand-heading">
            <Link to="/" className="site-footer-brand-link" aria-label="Swasthya home">
              <Logo size={48} />
              <strong className="brand-name" id="footer-brand-heading">
                Swasthya
              </strong>
            </Link>
            <p className="script">Real food. Real data. Real progress.</p>
            <p className="muted">
              Your companion for understanding nutrition, tracking meals, and building healthier habits.
            </p>
          </section>
          <nav className="site-footer-nav" aria-labelledby="footer-nav-heading">
            <h2 id="footer-nav-heading" className="site-footer-heading">
              Explore
            </h2>
            <ul>
              {NAV_LINKS.map((item) => (
                <li key={item.to}>
                  <NavLink to={item.to} end={"end" in item ? item.end : undefined}>
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <section className="site-footer-about" aria-labelledby="footer-about-heading">
            <h2 id="footer-about-heading" className="site-footer-heading">
              About Swasthya
            </h2>
            <p className="muted">
              Swasthya helps you track food intake, understand nutrition, and monitor your progress using
              verified nutrition data. Meals are stored only after the server calculates them from the dataset.
            </p>
          </section>
        </div>
        <div className="site-footer-bar">
          <p>© {year} Swasthya. All rights reserved.</p>
          <p>Built for healthier everyday choices.</p>
        </div>
      </div>
    </footer>
  );
}

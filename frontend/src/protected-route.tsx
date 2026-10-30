import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { api } from "./api";
import { profileComplete, type Profile } from "./pages";
import { useSession } from "./session";

export const LOGIN_NOTICE = "Sign in to log meals and view your personal progress.";

const AUTH_PATHS = new Set(["/login", "/register", "/forgot", "/reset-password"]);
const RETURN_PATH = /^\/(log|dashboard|profile|onboarding|today|chat|targets|settings|meals(\/\d+)?|coach|plan|diary|progress)$/;

export function safeReturnPath(from: unknown): string | null {
  const path =
    typeof from === "string"
      ? from
      : from && typeof from === "object" && "pathname" in from
        ? String((from as { pathname: unknown }).pathname)
        : "";
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\")) return null;
  const pathname = path.split("?")[0];
  if (AUTH_PATHS.has(pathname) || pathname === "/") return null;
  return RETURN_PATH.test(pathname) ? pathname : null;
}

export function RequireAuth() {
  const { user, ready } = useSession();
  const location = useLocation();

  if (!ready) return <p className="muted page">Loading…</p>;
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: { pathname: location.pathname }, notice: LOGIN_NOTICE }}
      />
    );
  }
  return <Outlet />;
}

export function RequireCompleteProfile() {
  const { user } = useSession();
  const [status, setStatus] = useState<"loading" | "ready" | "incomplete">("loading");

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    api<Profile>("/api/profile/")
      .then((profile) => {
        if (!cancelled) setStatus(profileComplete(profile) ? "ready" : "incomplete");
      })
      .catch(() => {
        if (!cancelled) setStatus("incomplete");
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (status === "loading") return <p className="muted page">Loading…</p>;
  if (status === "incomplete") return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

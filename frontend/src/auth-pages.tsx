import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { Logo } from "./logo";
import { profileComplete, type Profile } from "./pages";
import { LOGIN_NOTICE, safeReturnPath } from "./protected-route";
import { useSession } from "./session";

type AuthLocationState = { from?: unknown; notice?: string } | null;

type Mode = "login" | "register" | "forgot";

function errors(err: unknown) {
  if (err instanceof ApiError) {
    const first = Object.values(err.details).flat()[0];
    return first || err.message;
  }
  return "The request did not finish. Try again.";
}

function EyeIcon({ off }: { off?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"
      />
      <circle cx="12" cy="12" r="2.4" fill="none" stroke="currentColor" strokeWidth="1.8" />
      {off ? <path d="M4 20 20 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /> : null}
    </svg>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  placeholder: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <label>
      {label}
      <span className="password-row">
        <input
          type={visible ? "text" : "password"}
          value={value}
          autoComplete={autoComplete}
          placeholder={placeholder}
          required
          minLength={8}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          className="text-link password-toggle"
          type="button"
          aria-label={visible ? "Hide password" : "Show password"}
          onClick={() => setVisible((current) => !current)}
        >
          <EyeIcon off={visible} />
        </button>
      </span>
    </label>
  );
}

function LeafSprig({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 120 120" aria-hidden="true">
      <path d="M38 108C40 72 68 44 112 22" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M72 58c14-16 28-24 40-32-22 8-34 24-40 32Z" fill="currentColor" />
      <path d="M58 76c12-14 24-22 36-30-18 10-28 22-36 30Z" fill="currentColor" opacity="0.7" />
      <path d="M48 92c10-12 20-20 32-28-16 10-24 20-32 28Z" fill="currentColor" opacity="0.45" />
    </svg>
  );
}

function AuthLeaves() {
  return (
    <>
      <LeafSprig className="auth-leaf auth-leaf-tr" />
      <LeafSprig className="auth-leaf auth-leaf-bl" />
    </>
  );
}

function Brand({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="auth-brand">
      <Link to="/" className="brand auth-brand-link" aria-label="Swasthya home">
        <span className="auth-mark">
          <Logo size={64} />
        </span>
        <strong className="brand-name">Swasthya</strong>
      </Link>
      <h1>{title}</h1>
      <p className="muted">{copy}</p>
    </div>
  );
}

function modeFromPath(pathname: string): Mode {
  if (pathname.startsWith("/register")) return "register";
  if (pathname.startsWith("/forgot")) return "forgot";
  return "login";
}

export function AuthScreen() {
  const { user, ready, login, register } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>(() => modeFromPath(location.pathname));
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(() => {
    const state = location.state as AuthLocationState;
    return state?.notice ?? null;
  });
  const [busy, setBusy] = useState(false);
  const from = (location.state as AuthLocationState)?.from;

  useEffect(() => {
    setMode(modeFromPath(location.pathname));
    setError(null);
  }, [location.pathname]);

  useEffect(() => {
    const state = location.state as AuthLocationState;
    if (state?.notice) setNotice(state.notice);
  }, [location.state]);

  useEffect(() => {
    if (!ready || !user || mode === "forgot") return;
    const intended = safeReturnPath(from);
    api<Profile>("/api/profile/")
      .then((profile) => navigate(intended ?? (profileComplete(profile) ? "/today" : "/onboarding"), { replace: true }))
      .catch(() => navigate(intended ?? "/onboarding", { replace: true }));
  }, [ready, user, mode, from, navigate]);

  function switchMode(next: Mode) {
    setError(null);
    setNotice(next === "login" && from ? LOGIN_NOTICE : null);
    setPassword("");
    setConfirm("");
    setMode(next);
    const path = next === "register" ? "/register" : next === "forgot" ? "/forgot" : "/login";
    navigate(path, { state: from ? { from, notice: next === "login" ? LOGIN_NOTICE : undefined } : undefined });
  }

  async function onLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(errors(err));
      if (from) setNotice(LOGIN_NOTICE);
    } finally {
      setBusy(false);
    }
  }

  async function onRegister(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await register(email, name, password);
    } catch (err) {
      setError(errors(err));
    } finally {
      setBusy(false);
    }
  }

  async function onForgot(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const body = await api<{ message: string }>("/api/auth/password-reset/", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setPassword("");
      setConfirm("");
      setMode("login");
      setNotice(body.message);
      navigate("/login", { state: { from, notice: body.message } });
    } catch (err) {
      setError(errors(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      {mode === "login" && (
        <form className="card auth-card stack" onSubmit={onLogin}>
          <AuthLeaves />
          <Brand title="Welcome back" copy="Log in to track meals and see your progress." />
          <label>
            Email address
            <input
              type="email"
              value={email}
              autoComplete="email"
              placeholder="you@example.com"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <PasswordField
            label="Password"
            value={password}
            autoComplete="current-password"
            placeholder="Enter your password"
            onChange={setPassword}
          />
          <p className="forgot-row">
            <button className="text-link" type="button" onClick={() => switchMode("forgot")}>
              Forgot password?
            </button>
          </p>
          {notice && <p className="banner" role="status">{notice}</p>}
          {error && <p className="banner error" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? "Logging in…" : "Log In"}</button>
          <p className="muted auth-switch">
            New to Swasthya?{" "}
            <button className="text-link" type="button" onClick={() => switchMode("register")}>
              Sign up
            </button>
          </p>
        </form>
      )}

      {mode === "register" && (
        <form className="card auth-card stack" onSubmit={onRegister}>
          <AuthLeaves />
          <Brand title="Create your account" copy="Set up your profile and start logging meals." />
          <label>
            Full name
            <input
              value={name}
              autoComplete="name"
              placeholder="Enter your full name"
              required
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label>
            Email address
            <input
              type="email"
              value={email}
              autoComplete="email"
              placeholder="you@example.com"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <PasswordField
            label="Password"
            value={password}
            autoComplete="new-password"
            placeholder="Enter your password"
            onChange={setPassword}
          />
          <PasswordField
            label="Confirm password"
            value={confirm}
            autoComplete="new-password"
            placeholder="Confirm your password"
            onChange={setConfirm}
          />
          {error && <p className="banner error" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? "Creating account…" : "Create Account"}</button>
          <p className="muted auth-switch">
            Already have an account?{" "}
            <button className="text-link" type="button" onClick={() => switchMode("login")}>
              Log in
            </button>
          </p>
        </form>
      )}

      {mode === "forgot" && (
        <form className="card auth-card stack" onSubmit={onForgot}>
          <AuthLeaves />
          <Brand
            title="Reset your password"
            copy="Enter your email address and we’ll send you a secure link to reset your password."
          />
          <label>
            Email address
            <input
              type="email"
              value={email}
              autoComplete="email"
              placeholder="you@example.com"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          {error && <p className="banner error" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? "Sending…" : "Send Reset Link"}</button>
          <p className="muted auth-switch">
            <button className="text-link" type="button" onClick={() => switchMode("login")}>
              ← Back to Log In
            </button>
          </p>
        </form>
      )}
    </div>
  );
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!uid || !token) {
      setError("This reset link is incomplete.");
      setReady(false);
      return;
    }
    api("/api/auth/password-reset/validate/", {
      method: "POST",
      body: JSON.stringify({ uid, token }),
    })
      .then(() => setReady(true))
      .catch((err) => {
        setReady(false);
        setError(errors(err));
      });
  }, [uid, token]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const body = await api<{ message: string }>("/api/auth/password-reset/confirm/", {
        method: "POST",
        body: JSON.stringify({ uid, token, password }),
      });
      navigate("/login", { replace: true, state: { notice: body.message } });
    } catch (err) {
      setError(errors(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="card auth-card stack" onSubmit={onSubmit}>
        <AuthLeaves />
        <Brand title="Choose a new password" copy="This link works once and expires after 24 hours." />
        {error && <p className="banner error" role="alert">{error}</p>}
        {ready ? (
          <>
            <PasswordField
              label="New password"
              value={password}
              autoComplete="new-password"
              placeholder="Enter your password"
              onChange={setPassword}
            />
            <PasswordField
              label="Confirm password"
              value={confirm}
              autoComplete="new-password"
              placeholder="Confirm your password"
              onChange={setConfirm}
            />
            <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save new password"}</button>
          </>
        ) : (
          <p className="muted">{error ? "Request a new reset link from the login card." : "Checking this reset link…"}</p>
        )}
        <p className="muted auth-switch">
          <Link className="text-link" to="/login">← Back to Log In</Link>
        </p>
      </form>
    </div>
  );
}

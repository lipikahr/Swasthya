import { useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { LoginPage, RegisterPage } from "./auth-pages";
import { api } from "./api";
import {
  ChatPage,
  DashboardPage,
  MealDetailPage,
  MealsPage,
  OnboardingPage,
  SettingsPage,
  TargetsPage,
  profileComplete,
  type Profile,
} from "./pages";
import { useSession } from "./session";

function Guard() {
  const { user, ready } = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!user) return;
    api<Profile>("/api/profile/")
      .then(setProfile)
      .finally(() => setChecked(true));
  }, [user]);

  if (!ready || (user && !checked)) return <p className="muted page">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!profile || !profileComplete(profile)) return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

function Shell() {
  return (
    <div className="shell">
      <aside>
        <p className="mark">Swasthya</p>
        <nav>
          <NavLink to="/" end>
            Today
          </NavLink>
          <NavLink to="/chat">Log</NavLink>
          <NavLink to="/meals">Meals</NavLink>
          <NavLink to="/targets">Targets</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
      </aside>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

function SignedIn() {
  const { user, ready } = useSession();
  if (!ready) return <p className="muted page">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<SignedIn />}>
        <Route path="/onboarding" element={<OnboardingPage />} />
      </Route>
      <Route element={<Guard />}>
        <Route element={<Shell />}>
          <Route index element={<DashboardPage />} />
          <Route path="meals" element={<MealsPage />} />
          <Route path="meals/:id" element={<MealDetailPage />} />
          <Route path="targets" element={<TargetsPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./app-shell";
import { AuthScreen, ResetPasswordPage } from "./auth-pages";
import { AuthLayout } from "./health-carousel";
import { NutritionDashboard } from "./dashboard-page";
import { DiaryPage } from "./diary-page";
import { LogMealPage } from "./log-meal-page";
import { MealDetailPage } from "./pages";
import { PlanPage } from "./plan-page";
import { ProfilePage } from "./profile-page";
import { RequireAuth, RequireCompleteProfile } from "./protected-route";
import { SettingsPage } from "./settings-page";
import { LandingPage } from "./landing-page";
import { SiteFooter } from "./site-footer";
import { SiteNav } from "./site-nav";
import { TodayPage } from "./today-page";

function SiteFrame() {
  const { pathname } = useLocation();
  return (
    <div className={pathname === "/" ? "shell is-landing" : "shell"}>
      <SiteNav />
      <main>
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<SiteFrame />}>
        <Route path="/" element={<LandingPage />} />
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<AuthScreen />} />
          <Route path="/register" element={<AuthScreen />} />
          <Route path="/forgot" element={<AuthScreen />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>
        <Route path="/home" element={<Navigate to="/" replace />} />
        <Route path="/recipes/*" element={<Navigate to="/" replace />} />
        <Route path="/groceries" element={<Navigate to="/" replace />} />
        <Route path="/suggestions" element={<Navigate to="/" replace />} />
        <Route path="/planner" element={<Navigate to="/plan" replace />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/onboarding" element={<ProfilePage />} />
        <Route element={<RequireCompleteProfile />}>
          <Route element={<AppShell />}>
            <Route path="/today" element={<TodayPage />} />
            <Route path="/plan" element={<PlanPage />} />
            <Route path="/coach" element={<LogMealPage />} />
            <Route path="/diary" element={<DiaryPage />} />
            <Route path="/progress" element={<NutritionDashboard />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/meals/:id" element={<MealDetailPage />} />
          </Route>
          <Route path="/log" element={<Navigate to="/coach" replace />} />
          <Route path="/chat" element={<Navigate to="/coach" replace />} />
          <Route path="/dashboard" element={<Navigate to="/progress" replace />} />
          <Route path="/profile" element={<Navigate to="/settings" replace />} />
          <Route path="/targets" element={<Navigate to="/settings?tab=goals" replace />} />
          <Route path="/meals" element={<Navigate to="/diary" replace />} />
          <Route path="/planner" element={<Navigate to="/plan" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}

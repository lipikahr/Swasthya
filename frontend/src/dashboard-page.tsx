import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";
import { localIsoDay, monthBounds, shiftDay, shiftMonth, startOfWeek } from "./dates";
import { CalendarIcon, ChartIcon, ChevronLeftIcon, ChevronRightIcon, FlameIcon, PlusIcon, TargetIcon } from "./icons";
import "./progress.css";

type Target = {
  calories: string;
  protein_g: string;
  carbohydrates_g: string;
  fat_g: string;
  fibre_g: string;
  source: string;
};

type DayProgress = {
  date: string;
  meal_count: number;
  consumed: Record<string, string | null>;
  remaining: Record<string, string | null> | null;
  goal_status: string;
  goal_label: string;
  target_calories: string | null;
  tolerance?: string;
};

type Dashboard = {
  date: string;
  progress: DayProgress;
  target: Target | null;
  streaks: { weekly: number; monthly: number; rule: string };
  most_logged_foods?: Array<{ name: string; times: number }>;
};

type RangeResponse = {
  start: string;
  end: string;
  days: DayProgress[];
  summary: { met: number; below: number; above: number; no_data: number; no_target?: number };
};

const ROWS = [
  ["energy_kcal", "calories", "Calories", "kcal"],
  ["protein_g", "protein_g", "Protein", "g"],
  ["carb_g", "carbohydrates_g", "Carbs", "g"],
  ["fat_g", "fat_g", "Fat", "g"],
  ["fibre_g", "fibre_g", "Fibre", "g"],
] as const;

function messageFrom(err: unknown) {
  return err instanceof ApiError ? err.message : "The dashboard could not be loaded.";
}

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function ratio(consumed: string | null | undefined, target: string | null | undefined) {
  if (consumed == null || target == null) return null;
  const eaten = Number(consumed);
  const goal = Number(target);
  if (!Number.isFinite(eaten) || !Number.isFinite(goal) || goal <= 0) return null;
  return Math.min(100, (eaten / goal) * 100);
}

function statusMark(status: string) {
  if (status === "met") return "✓";
  if (status === "below") return "↓";
  if (status === "above") return "↑";
  if (status === "no_data") return "·";
  return "–";
}

export function NutritionDashboard() {
  const [anchor, setAnchor] = useState(() => localIsoDay());
  const [view, setView] = useState<"daily" | "weekly" | "monthly">("daily");
  const [data, setData] = useState<Dashboard | null>(null);
  const [range, setRange] = useState<RangeResponse | null>(null);
  const [error, setError] = useState("");

  const weekStart = useMemo(() => startOfWeek(anchor), [anchor]);
  const weekEnd = useMemo(() => shiftDay(weekStart, 6), [weekStart]);
  const month = useMemo(() => monthBounds(anchor), [anchor]);

  useEffect(() => {
    let cancelled = false;
    setError("");
    const rangeQuery =
      view === "weekly"
        ? `/api/progress/range/?start=${weekStart}&end=${weekEnd}`
        : view === "monthly"
          ? `/api/progress/range/?start=${month.start}&end=${month.end}`
          : null;
    Promise.all([
      api<Dashboard>(`/api/dashboard/?date=${anchor}`),
      rangeQuery ? api<RangeResponse>(rangeQuery) : Promise.resolve(null),
    ])
      .then(([dashboard, rangeBody]) => {
        if (cancelled) return;
        setData(dashboard);
        setRange(rangeBody);
      })
      .catch((err) => {
        if (!cancelled) setError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [anchor, view, weekStart, weekEnd, month.start, month.end]);

  if (error) return <p className="banner error" role="alert">{error}</p>;
  if (!data) return <p className="muted">Loading your nutrition…</p>;

  const progress = data.progress;
  const calorieRatio = ratio(progress.consumed.energy_kcal, progress.target_calories ?? data.target?.calories);
  const source = data.target?.source === "user_customized" ? "Your numbers" : data.target ? "System suggested" : "No target";
  const remainingCalories = progress.remaining?.calories;
  const remainingNumber = remainingCalories == null ? null : Number(remainingCalories);
  const remainingText =
    remainingNumber == null
      ? "Remaining calories are unknown."
      : remainingNumber >= 0
        ? `${amount(remainingCalories)} kcal remaining`
        : `${amount(String(Math.abs(remainingNumber)))} kcal above target`;

  function step(direction: number) {
    if (view === "monthly") setAnchor(shiftMonth(anchor, direction));
    else if (view === "weekly") setAnchor(shiftDay(weekStart, direction * 7));
    else setAnchor(shiftDay(anchor, direction));
  }

  return (
    <div className="fit-page progress-page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Progress</p>
          <h1>Your nutrition at a glance</h1>
          <p className="muted">Totals use saved meals only. A day with no meals is no data, not a miss.</p>
        </div>
        <Link className="button" to="/coach?compose=1"><PlusIcon /> Log a Meal</Link>
      </header>
      <div className="segment-row" role="tablist" aria-label="Progress view">
        {(["daily", "weekly", "monthly"] as const).map((name) => (
          <button key={name} type="button" className={view === name ? "" : "ghost"} onClick={() => setView(name)}>
            {name === "monthly" ? <CalendarIcon /> : <ChartIcon />}
            {name[0].toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
      <div className="progress-period">
        <button type="button" className="icon-nav ghost" aria-label="Previous" onClick={() => step(-1)}><ChevronLeftIcon /></button>
        <p className="muted">{view === "daily" ? anchor : view === "weekly" ? `${weekStart} – ${weekEnd}` : `${month.start} – ${month.end}`}</p>
        <button type="button" className="icon-nav ghost" aria-label="Next" onClick={() => step(1)}><ChevronRightIcon /></button>
      </div>
      <div className="fit-grid progress-layout">
        <section className="fit-scroll stack">
          {view === "daily" ? (
            <article className={`card goal-card is-${progress.goal_status}`}>
              <p className="eyebrow"><TargetIcon /> {progress.goal_label} {statusMark(progress.goal_status)}</p>
              <div className="ring-wrap">
                <div className="ring" style={{ ["--progress" as string]: calorieRatio ?? 0 }}>
                  <span>{calorieRatio == null ? "—" : `${Math.round(calorieRatio)}%`}</span>
                </div>
                <h2>{displayKcal(progress.consumed.energy_kcal)} / {data.target ? displayKcal(data.target.calories) : "no target"} kcal</h2>
              </div>
              <p className="muted">{remainingText}. Goal met means intake is within {(Number(progress.tolerance ?? 0.05) * 100).toFixed(0)}% of the calorie target.</p>
              {progress.meal_count === 0 ? <p className="banner">No meals are saved for this day yet.</p> : <p className="muted"><Link to={`/diary`}>Open {anchor} in Diary</Link></p>}
            </article>
          ) : null}
          {view === "weekly" && range ? (
            <article className="card stack">
              <p className="eyebrow">Seven-day intake</p>
              <p className="muted">{range.summary.met} days met the calorie target. {range.summary.below + range.summary.above} days need attention. {range.summary.no_data} days have no saved meals.{range.summary.no_target ? ` ${range.summary.no_target} days have meals but no calorie target.` : ""}</p>
              <ul className="week-chart" aria-label="Weekly calorie progress">
                {range.days.map((day) => {
                  const height = ratio(day.consumed.energy_kcal, day.target_calories) ?? 0;
                  return (
                    <li key={day.date} className={`is-${day.goal_status}`}>
                      <Link to="/diary" className="week-col" title={`${day.date}: ${day.goal_label}`} onClick={() => sessionStorage.setItem("swasthya.diaryDay", day.date)}>
                        <span className="week-bar" style={{ height: `${Math.max(8, height)}%` }} />
                      </Link>
                      <strong>{statusMark(day.goal_status)}</strong>
                      <span>{day.date.slice(8)}</span>
                      <span className="muted">{day.goal_label}</span>
                    </li>
                  );
                })}
              </ul>
              <p className="muted">Legend: ✓ Goal met · ↓ Below target · ↑ Above target · · No data. Open a day in Diary to see the meals.</p>
            </article>
          ) : null}
          {view === "monthly" && range ? (
            <article className="card stack">
              <p className="eyebrow">Month overview</p>
              <p className="muted">{range.summary.met} days met · {range.summary.below} below · {range.summary.above} above · {range.summary.no_data} with no meals. This is tracking, not a health outcome.</p>
              <p className="muted"><Link to="/diary">Open this month in Diary</Link> to browse meals by date.</p>
              <ul className="week-chart" aria-label="Monthly calorie trend">
                {range.days.filter((_, index) => index % 2 === 0 || range.days.length <= 16).slice(0, 16).map((day) => {
                  const height = ratio(day.consumed.energy_kcal, day.target_calories) ?? 0;
                  return (
                    <li key={day.date} className={`is-${day.goal_status}`}>
                      <div className="week-col" title={`${day.date}: ${day.goal_label}`}>
                        <span className="week-bar" style={{ height: `${Math.max(8, height)}%` }} />
                      </div>
                      <span>{day.date.slice(8)}</span>
                    </li>
                  );
                })}
              </ul>
            </article>
          ) : null}
        </section>
        <aside className="card stack">
          <h2><TargetIcon /> Daily goals</h2>
          <div className="macro-list">
            {ROWS.map(([consumedKey, targetKey, label, unit]) => {
              const width = ratio(progress.consumed[consumedKey], data.target?.[targetKey]);
              return (
                <div key={consumedKey}>
                  <p>{label} · {amount(progress.consumed[consumedKey])} / {data.target ? amount(data.target[targetKey]) : "not set"} {unit}</p>
                  <div className={`bar is-${consumedKey}`} aria-hidden="true"><i style={{ width: `${width ?? 0}%` }} /></div>
                </div>
              );
            })}
          </div>
          <p className="muted">Target source: {source}. {progress.meal_count} saved meal{progress.meal_count === 1 ? "" : "s"}.</p>
          <div className="progress-block">
            <p className="eyebrow"><FlameIcon /> Logging streaks</p>
            <div className="streak-stats">
              <div>
                <strong>{data.streaks.weekly}</strong>
                <span>{data.streaks.weekly === 1 ? "Day" : "Days"} this week</span>
              </div>
              <div>
                <strong>{data.streaks.monthly}</strong>
                <span>{data.streaks.monthly === 1 ? "Day" : "Days"} this month</span>
              </div>
            </div>
            <p className="muted">{data.streaks.rule}</p>
          </div>
          {(data.most_logged_foods ?? []).length ? (
            <div className="progress-block">
              <p className="eyebrow">Most logged foods</p>
              <p className="muted">Last 28 days</p>
              <ul className="logged-foods">
                {data.most_logged_foods?.map((food) => (
                  <li key={food.name}>
                    <span>{food.name}</span>
                    <strong>{food.times}</strong>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <Link className="text-link" to="/settings?tab=goals">Edit goals</Link>
        </aside>
      </div>
    </div>
  );
}

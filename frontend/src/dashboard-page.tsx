import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";

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
  weekly?: { consumed_calories: string | null; target_calories: string; derived_from_daily: boolean } | null;
  most_logged_foods?: Array<{ name: string; times: number }>;
};

type RangeResponse = {
  start: string;
  end: string;
  days: DayProgress[];
  summary: { met: number; below: number; above: number; no_data: number; no_target?: number };
};

type Meal = {
  id: number;
  timestamp: string;
  meal_type: string;
  items: Array<{ id: number; food_name: string; quantity: string; unit: string; nutrition_snapshot: Record<string, string | null> }>;
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

function parseDay(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function isoDay(value: Date) {
  return value.toISOString().slice(0, 10);
}

function shiftDay(iso: string, days: number) {
  const value = parseDay(iso);
  value.setUTCDate(value.getUTCDate() + days);
  return isoDay(value);
}

function startOfWeek(iso: string) {
  const value = parseDay(iso);
  const weekday = (value.getUTCDay() + 6) % 7;
  value.setUTCDate(value.getUTCDate() - weekday);
  return isoDay(value);
}

function monthBounds(iso: string) {
  const value = parseDay(iso);
  const start = new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), 1));
  const end = new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth() + 1, 0));
  return { start: isoDay(start), end: isoDay(end) };
}

function statusMark(status: string) {
  if (status === "met") return "✓";
  if (status === "below") return "↓";
  if (status === "above") return "↑";
  if (status === "no_data") return "·";
  return "–";
}

export function NutritionDashboard() {
  const [anchor, setAnchor] = useState(() => new Date().toISOString().slice(0, 10));
  const [view, setView] = useState<"daily" | "weekly" | "monthly">("daily");
  const [data, setData] = useState<Dashboard | null>(null);
  const [range, setRange] = useState<RangeResponse | null>(null);
  const [meals, setMeals] = useState<Meal[] | null>(null);
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
      api<{ results: Meal[] }>(`/api/meals/?date=${anchor}`),
      rangeQuery ? api<RangeResponse>(rangeQuery) : Promise.resolve(null),
    ])
      .then(([dashboard, mealBody, rangeBody]) => {
        if (cancelled) return;
        setData(dashboard);
        setMeals(mealBody.results);
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

  return (
    <div className="dash-layout">
      <section className="stack">
        <header className="page-head">
          <div>
            <p className="eyebrow">Progress</p>
            <h1>Your Nutrition at a Glance</h1>
            <p className="muted">Totals use saved meals only. A day with no meals is no data, not a miss. Intake above the calorie band is not treated as success.</p>
          </div>
          <Link className="button" to="/coach?compose=1">Log a Meal</Link>
        </header>
        <div className="segment-row" role="tablist" aria-label="Progress view">
          {(["daily", "weekly", "monthly"] as const).map((name) => (
            <button key={name} type="button" className={view === name ? "" : "ghost"} onClick={() => setView(name)}>
              {name[0].toUpperCase() + name.slice(1)}
            </button>
          ))}
        </div>
        <div className="row-actions">
          <button type="button" className="ghost" onClick={() => setAnchor(shiftDay(anchor, view === "monthly" ? -30 : view === "weekly" ? -7 : -1))}>Previous</button>
          <p className="muted">{view === "daily" ? anchor : view === "weekly" ? `${weekStart} – ${weekEnd}` : `${month.start} – ${month.end}`}</p>
          <button type="button" className="ghost" onClick={() => setAnchor(shiftDay(anchor, view === "monthly" ? 30 : view === "weekly" ? 7 : 1))}>Next</button>
        </div>
        {view === "daily" ? (
          <>
            <article className={`card goal-card is-${progress.goal_status}`}>
              <p className="eyebrow">{progress.goal_label} {statusMark(progress.goal_status)}</p>
              <h2>{displayKcal(progress.consumed.energy_kcal)} / {data.target ? displayKcal(data.target.calories) : "no target"} kcal</h2>
              <p className="muted">{remainingText}. Goal met means intake is within {(Number(progress.tolerance ?? 0.05) * 100).toFixed(0)}% of the calorie target.</p>
            </article>
            {progress.meal_count === 0 ? <p className="banner">No meals are saved for this day yet, so there is not enough data for a goal result.</p> : null}
            <h2>Meals on this day</h2>
            <ul className="plain">
              {(meals ?? []).map((meal) => (
                <li key={meal.id} className="card meal-row">
                  <div>
                    <Link to={`/meals/${meal.id}`}>{meal.meal_type === "snack" ? "Snack" : meal.meal_type}</Link>
                    <p className="muted">{new Date(meal.timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</p>
                    {meal.items.map((item) => (
                      <p key={item.id}>
                        {item.food_name} · {amount(item.quantity)} {item.unit}
                        {" · "}{displayKcal(item.nutrition_snapshot.energy_kcal)} kcal
                      </p>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </>
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
                    <div className="week-col" title={`${day.date}: ${day.goal_label}`}>
                      <span className="week-bar" style={{ height: `${Math.max(8, height)}%` }} />
                    </div>
                    <strong>{statusMark(day.goal_status)}</strong>
                    <span>{day.date.slice(8)}</span>
                    <span className="muted">{day.goal_label}</span>
                  </li>
                );
              })}
            </ul>
            <p className="muted">Legend: ✓ Goal met · ↓ Below target · ↑ Above target · · No data</p>
          </article>
        ) : null}
        {view === "monthly" && range ? (
          <article className="card stack">
            <p className="eyebrow">Month overview</p>
            <p className="muted">{range.summary.met} days met · {range.summary.below} below · {range.summary.above} above · {range.summary.no_data} with no meals. This is tracking, not a health outcome.</p>
            <div className="month-grid">
              {range.days.map((day) => (
                <button key={day.date} type="button" className={`month-cell is-${day.goal_status}`} onClick={() => { setAnchor(day.date); setView("daily"); }}>
                  <span>{day.date.slice(8)}</span>
                  <strong>{statusMark(day.goal_status)}</strong>
                  <span className="visually-hidden">{day.goal_label}</span>
                </button>
              ))}
            </div>
          </article>
        ) : null}
      </section>
      <aside className="card stack">
        <h2>Daily Goals</h2>
        <div className="ring-wrap">
          <div className="ring" style={{ ["--progress" as string]: calorieRatio ?? 0 }}>
            <span>{calorieRatio == null ? "—" : `${Math.round(calorieRatio)}%`}</span>
          </div>
          <p className="muted">{amount(progress.consumed.energy_kcal)} / {data.target ? amount(data.target.calories) : "no target"} kcal</p>
          <p className="muted">{progress.goal_label} {statusMark(progress.goal_status)}</p>
        </div>
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
        <p className="eyebrow">Logging streaks</p>
        <p className="muted">{data.streaks.weekly} day{data.streaks.weekly === 1 ? "" : "s"} this week · {data.streaks.monthly} day{data.streaks.monthly === 1 ? "" : "s"} this month. {data.streaks.rule}</p>
        {data.weekly ? (
          <div className="ring-wrap">
            <p className="eyebrow">Weekly calories</p>
            <div className="ring" style={{ ["--progress" as string]: ratio(data.weekly.consumed_calories, data.weekly.target_calories) ?? 0 }}>
              <span>{ratio(data.weekly.consumed_calories, data.weekly.target_calories) == null ? "—" : `${Math.round(ratio(data.weekly.consumed_calories, data.weekly.target_calories) ?? 0)}%`}</span>
            </div>
            <p className="muted">
              {amount(data.weekly.consumed_calories)} / {amount(data.weekly.target_calories)} kcal
              {data.weekly.derived_from_daily ? " · weekly target is daily × 7" : " · weekly target you set"}
            </p>
          </div>
        ) : null}
        {(data.most_logged_foods ?? []).length ? (
          <div>
            <p className="eyebrow">Most logged foods (28 days)</p>
            <ul className="plain">
              {data.most_logged_foods?.map((food) => (
                <li key={food.name}>{food.name} · {food.times}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <Link to="/settings?tab=goals">Edit goals</Link>
      </aside>
    </div>
  );
}

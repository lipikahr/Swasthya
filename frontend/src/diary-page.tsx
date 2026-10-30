import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";

type DayProgress = {
  date: string;
  meal_count: number;
  consumed: Record<string, string | null>;
  remaining: Record<string, string | null> | null;
  goal_status: string;
  goal_label: string;
  target_calories: string | null;
};

type Meal = {
  id: number;
  meal_type: string;
  timestamp: string;
  items: Array<{ id: number; food_name: string; quantity: string; unit: string; nutrition_snapshot: Record<string, string | null>; provenance?: string }>;
};

const GROUPS = ["breakfast", "lunch", "snack", "dinner"] as const;

function isoDay(value: Date) {
  return value.toISOString().slice(0, 10);
}

function parseDay(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function shift(iso: string, days: number) {
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

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function DiaryPage() {
  const [anchor, setAnchor] = useState(() => new Date().toISOString().slice(0, 10));
  const [days, setDays] = useState<DayProgress[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [error, setError] = useState("");
  const weekStart = useMemo(() => startOfWeek(anchor), [anchor]);
  const weekEnd = useMemo(() => shift(weekStart, 6), [weekStart]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<{ days: DayProgress[] }>(`/api/progress/range/?start=${weekStart}&end=${weekEnd}`),
      api<{ results: Meal[] }>(`/api/meals/?date=${anchor}`),
    ])
      .then(([range, mealBody]) => {
        if (cancelled) return;
        setDays(range.days);
        setMeals(mealBody.results);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Diary could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [anchor, weekStart, weekEnd]);

  const selected = days.find((day) => day.date === anchor);

  return (
    <div className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">Diary</p>
          <h1>Saved meals</h1>
          <p className="muted">Only confirmed meals appear here.</p>
        </div>
        <Link className="button" to="/coach?compose=1">Add meal</Link>
      </header>
      {error ? <p className="banner error" role="alert">{error}</p> : null}
      <div className="row-actions">
        <button type="button" className="ghost" onClick={() => setAnchor(shift(weekStart, -7))}>Previous week</button>
        <button type="button" className="ghost" onClick={() => setAnchor(new Date().toISOString().slice(0, 10))}>Today</button>
        <button type="button" className="ghost" onClick={() => setAnchor(shift(weekStart, 7))}>Next week</button>
      </div>
      <div className="week-strip" role="list">
        {days.map((day) => (
          <button key={day.date} type="button" className={day.date === anchor ? "" : "ghost"} onClick={() => setAnchor(day.date)}>
            {day.date.slice(8)}
            <span className="muted">{day.goal_label}</span>
          </button>
        ))}
      </div>
      <aside className="card">
        <p className="eyebrow">Day summary</p>
        <p>{displayKcal(selected?.consumed.energy_kcal)} / {selected?.target_calories ? displayKcal(selected.target_calories) : "no target"} kcal</p>
        <p className="muted">{selected?.goal_label}. {selected?.meal_count ?? 0} saved meals.</p>
      </aside>
      {GROUPS.map((group) => {
        const groupMeals = meals.filter((meal) => meal.meal_type === group);
        return (
          <section key={group}>
            <h2>{group[0].toUpperCase() + group.slice(1)}</h2>
            {groupMeals.length === 0 ? <p className="muted">No {group} logged.</p> : null}
            <ul className="plain">
              {groupMeals.map((meal) => (
                <li key={meal.id} className="card">
                  {meal.items.map((item) => (
                    <p key={item.id}>
                      {item.food_name} · {amount(item.quantity)} {item.unit} · {displayKcal(item.nutrition_snapshot.energy_kcal)} kcal
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

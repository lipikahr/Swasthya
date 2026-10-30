import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";
import {
  formatLong,
  formatMonth,
  localIsoDay,
  monthBounds,
  monthCells,
  shiftDay,
  shiftMonth,
  startOfWeek,
  weekdayShort,
} from "./dates";
import { BookIcon, CalendarIcon, ChartIcon, ChevronLeftIcon, ChevronRightIcon, MEAL_ICONS, PlusIcon, TrashIcon } from "./icons";
import "./diary.css";

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
const VIEWS = ["day", "week", "month"] as const;

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function DiaryPage() {
  const [anchor, setAnchor] = useState(() => sessionStorage.getItem("swasthya.diaryDay") || localIsoDay());
  const [view, setView] = useState<(typeof VIEWS)[number]>("day");
  const [days, setDays] = useState<DayProgress[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const weekStart = useMemo(() => startOfWeek(anchor), [anchor]);
  const weekEnd = useMemo(() => shiftDay(weekStart, 6), [weekStart]);
  const month = useMemo(() => monthBounds(anchor), [anchor]);
  const cells = useMemo(() => monthCells(anchor), [anchor]);

  useEffect(() => {
    let cancelled = false;
    const range = view === "month" ? month : { start: weekStart, end: weekEnd };
    Promise.all([
      api<{ days: DayProgress[] }>(`/api/progress/range/?start=${range.start}&end=${range.end}`),
      api<{ results: Meal[] }>(`/api/meals/?date=${anchor}`),
    ])
      .then(([body, mealBody]) => {
        if (cancelled) return;
        setDays(body.days);
        setMeals(mealBody.results);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Diary could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [anchor, view, weekStart, weekEnd, month.start, month.end]);

  const selected = days.find((day) => day.date === anchor);
  const lookup = Object.fromEntries(days.map((day) => [day.date, day]));

  function step(direction: number) {
    if (view === "month") setAnchor(shiftMonth(anchor, direction));
    else if (view === "week") setAnchor(shiftDay(weekStart, direction * 7));
    else setAnchor(shiftDay(anchor, direction));
  }

  async function changeType(meal: Meal, mealType: string) {
    setBusy(true);
    try {
      await api(`/api/meals/${meal.id}/`, { method: "PATCH", body: JSON.stringify({ meal_type: mealType }) });
      setMeals((current) => current.map((item) => (item.id === meal.id ? { ...item, meal_type: mealType } : item)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That meal could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  async function removeMeal(meal: Meal) {
    setBusy(true);
    try {
      await api(`/api/meals/${meal.id}/`, { method: "DELETE" });
      setMeals((current) => current.filter((item) => item.id !== meal.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That meal could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fit-page diary-page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Diary</p>
          <h1>Saved meals</h1>
          <p className="muted">Only confirmed meals appear here. Open a day, a week, or a month.</p>
        </div>
        <Link className="button" to="/coach?compose=1"><PlusIcon /> Add meal</Link>
      </header>
      {error ? <p className="banner error" role="alert">{error}</p> : null}
      <div className="diary-toolbar">
        <div className="segment-row" role="tablist" aria-label="Diary view">
          {VIEWS.map((name) => (
            <button key={name} type="button" className={view === name ? "" : "ghost"} onClick={() => setView(name)}>
              {name === "month" ? <CalendarIcon /> : name === "week" ? <ChartIcon /> : <BookIcon />}
              {name[0].toUpperCase() + name.slice(1)}
            </button>
          ))}
        </div>
        <button type="button" className="icon-nav ghost" aria-label="Previous" onClick={() => step(-1)}><ChevronLeftIcon /></button>
        <button type="button" className="ghost" onClick={() => setAnchor(localIsoDay())}>Today</button>
        <button type="button" className="icon-nav ghost" aria-label="Next" onClick={() => step(1)}><ChevronRightIcon /></button>
        <label>
          Jump to date
          <input type="date" value={anchor} onChange={(event) => setAnchor(event.target.value)} />
        </label>
        <p className="muted">{view === "month" ? formatMonth(anchor) : view === "week" ? `${weekStart} – ${weekEnd}` : formatLong(anchor)}</p>
      </div>
      <div className="fit-grid diary-layout">
        <aside className="card fit-panel diary-cal">
          {view === "month" ? (
            <>
              <div className="diary-weekdays">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((name) => <span key={name}>{name}</span>)}</div>
              <div className="diary-month">
                {cells.map((iso, index) => {
                  if (!iso) return <span key={`blank-${index}`} className="diary-cell is-blank" />;
                  const day = lookup[iso];
                  return (
                    <button key={iso} type="button" className={`diary-cell ${iso === anchor ? "" : "ghost"} is-${day?.goal_status ?? "no_data"}`} onClick={() => { setAnchor(iso); setView("day"); }}>
                      {iso.slice(8)}
                      <span className="dots" aria-hidden="true">
                        {Array.from({ length: Math.min(day?.meal_count ?? 0, 4) }, (_, dot) => <i key={dot} className="dot" />)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="week-strip" role="list">
              {(view === "week" ? days : days.filter((day) => day.date >= weekStart && day.date <= weekEnd)).map((day) => (
                <button key={day.date} type="button" className={day.date === anchor ? "" : "ghost"} onClick={() => { setAnchor(day.date); setView("day"); }}>
                  {weekdayShort(day.date)}
                  <strong>{day.date.slice(8)}</strong>
                  <span className="muted">{day.meal_count} meal{day.meal_count === 1 ? "" : "s"}</span>
                </button>
              ))}
            </div>
          )}
        </aside>
        <section className="card fit-panel diary-day">
          <div className="diary-total">
            <p className="eyebrow">{formatLong(anchor)}</p>
            <p>{displayKcal(selected?.consumed.energy_kcal)} / {selected?.target_calories ? displayKcal(selected.target_calories) : "no target"} kcal · {selected?.meal_count ?? 0} saved meals</p>
          </div>
          <div className="fit-scroll diary-groups">
            {GROUPS.map((group) => {
              const Icon = MEAL_ICONS[group];
              const groupMeals = meals.filter((meal) => meal.meal_type === group);
              return (
                <article key={group} className="diary-group">
                  <h2><Icon /> {group[0].toUpperCase() + group.slice(1)}</h2>
                  {groupMeals.length === 0 ? <p className="muted">Nothing saved.</p> : null}
                  {groupMeals.map((meal) => (
                    <div key={meal.id} className="card diary-item">
                      {meal.items.map((item) => (
                        <p key={item.id}>
                          {item.food_name} · {amount(item.quantity)} {item.unit} · {displayKcal(item.nutrition_snapshot.energy_kcal)} kcal
                        </p>
                      ))}
                      <div className="diary-item-actions">
                        <label>
                          Meal
                          <select value={meal.meal_type} disabled={busy} onChange={(event) => void changeType(meal, event.target.value)}>
                            {GROUPS.map((option) => <option key={option} value={option}>{option}</option>)}
                          </select>
                        </label>
                        <button type="button" className="danger" disabled={busy} onClick={() => void removeMeal(meal)}><TrashIcon /> Remove</button>
                      </div>
                    </div>
                  ))}
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}

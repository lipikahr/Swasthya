import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";

type Dashboard = {
  date: string;
  progress: {
    meal_count: number;
    consumed: Record<string, string | null>;
    remaining: Record<string, string | null> | null;
    goal_status: string;
    goal_label: string;
    target_calories: string | null;
  };
  target: { calories: string; protein_g: string; carbohydrates_g: string; fat_g: string; fibre_g: string } | null;
};

type Meal = {
  id: number;
  meal_type: string;
  timestamp: string;
  items: Array<{ id: number; food_name: string; quantity: string; unit: string; nutrition_snapshot: Record<string, string | null>; provenance?: string }>;
};

const GROUPS = ["breakfast", "lunch", "snack", "dinner"] as const;
const MACROS = [
  ["energy_kcal", "calories", "Calories", "kcal"],
  ["protein_g", "protein_g", "Protein", "g"],
  ["carb_g", "carbohydrates_g", "Carbs", "g"],
  ["fat_g", "fat_g", "Fat", "g"],
  ["fibre_g", "fibre_g", "Fibre", "g"],
] as const;

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

export function TodayPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api<Dashboard>("/api/dashboard/"), api<{ results: Meal[] }>("/api/meals/")])
      .then(([dashboard, mealBody]) => {
        if (cancelled) return;
        setData(dashboard);
        setMeals(mealBody.results.filter((meal) => meal.timestamp.slice(0, 10) === dashboard.date));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Today could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p className="banner error" role="alert">{error}</p>;
  if (!data) return <p className="muted">Loading today…</p>;

  const remaining = data.progress.remaining?.calories;
  const remainingNumber = remaining == null ? null : Number(remaining);
  const remainingText =
    remainingNumber == null
      ? "Remaining calories are unknown."
      : remainingNumber >= 0
        ? `${amount(remaining)} kcal remaining`
        : `${amount(String(Math.abs(remainingNumber)))} kcal above target`;

  return (
    <div className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">Today</p>
          <h1>{data.date}</h1>
          <p className="muted">Totals use saved meals only. Plans and drafts are not counted.</p>
        </div>
        <Link className="button" to="/coach?compose=1">Log a Meal</Link>
      </header>
      <article className={`card goal-card is-${data.progress.goal_status}`}>
        <p className="eyebrow">{data.progress.goal_label}</p>
        <h2>{displayKcal(data.progress.consumed.energy_kcal)} / {data.target ? displayKcal(data.target.calories) : "no target"} kcal</h2>
        <p className="muted">{remainingText}</p>
      </article>
      <div className="macro-list card">
        {MACROS.map(([consumedKey, targetKey, label, unit]) => {
          const width = ratio(data.progress.consumed[consumedKey], data.target?.[targetKey as keyof NonNullable<Dashboard["target"]>]);
          return (
            <div key={consumedKey}>
              <p>{label} · {amount(data.progress.consumed[consumedKey])} / {data.target ? amount(data.target[targetKey as keyof NonNullable<Dashboard["target"]>]) : "not set"} {unit}</p>
              <div className="bar" aria-hidden="true"><i style={{ width: `${width ?? 0}%` }} /></div>
            </div>
          );
        })}
      </div>
      {GROUPS.map((group) => {
        const groupMeals = meals.filter((meal) => meal.meal_type === group);
        return (
          <section key={group} className="stack">
            <h2>{group[0].toUpperCase() + group.slice(1)}</h2>
            {groupMeals.length === 0 ? <p className="muted">Nothing logged for {group} yet.</p> : null}
            <ul className="plain">
              {groupMeals.map((meal) => (
                <li key={meal.id} className="card">
                  {meal.items.map((item) => (
                    <p key={item.id}>
                      {item.food_name} · {amount(item.quantity)} {item.unit} · {displayKcal(item.nutrition_snapshot.energy_kcal)} kcal
                      {item.provenance === "user_provided" ? " · User-provided nutrition" : ""}
                    </p>
                  ))}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {data.progress.meal_count === 0 ? (
        <p className="banner">No meals are saved for today. <Link to="/coach">Open Coach</Link> or review the <Link to="/diary">Diary</Link>.</p>
      ) : null}
      <p className="muted"><Link to="/progress">Progress</Link></p>
    </div>
  );
}

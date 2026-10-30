import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";

type Home = {
  name: string;
  date: string;
  today: {
    meal_count: number;
    consumed: Record<string, string | null>;
    remaining: Record<string, string | null> | null;
    target: { calories: string; protein_g: string } | null;
  };
  week: {
    week_start: string;
    days_with_meals: number;
    meal_count: number;
    energy_kcal: string | null;
    energy_status: string;
    note: string;
  };
  groceries: {
    outstanding_count: number;
    items: { id: number; name: string; quantity: string; unit: string }[];
  };
  saved_recipes: { slug: string; title: string; nutrition_status: string }[];
  featured: { slug: string; title: string; summary: string; nutrition: { status: string } } | null;
  featured_reason: string;
};

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function HomePage() {
  const [data, setData] = useState<Home | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Home>("/api/home/")
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Something went wrong."));
  }, []);

  if (error) return <p className="banner error">{error}</p>;
  if (!data) return <p className="muted">Loading home…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">{data.date}</p>
          <h1>Hello, {data.name}</h1>
        </div>
        <Link className="button" to="/planner">
          Open the weekly planner
        </Link>
      </header>
      <div className="metric-grid">
        <article className="card metric">
          <p className="eyebrow">Calories today</p>
          <strong>{amount(data.today.consumed.energy_kcal)}</strong>
          <p className="muted">
            kcal logged
            {data.today.target ? ` · target ${amount(data.today.target.calories)}` : " · no target yet"}
            {data.today.remaining ? ` · remaining ${amount(data.today.remaining.calories)}` : ""}
          </p>
        </article>
        <article className="card metric">
          <p className="eyebrow">Protein today</p>
          <strong>{amount(data.today.consumed.protein_g)}</strong>
          <p className="muted">
            g logged
            {data.today.target ? ` · target ${amount(data.today.target.protein_g)}` : ""}
          </p>
        </article>
        <article className="card metric">
          <p className="eyebrow">This week</p>
          <strong>{data.week.meal_count}</strong>
          <p className="muted">
            logged meals · {data.week.days_with_meals} days
            {data.week.energy_status === "complete" ? ` · ${amount(data.week.energy_kcal)} kcal` : ""}
          </p>
          <p className="muted">{data.week.note}</p>
        </article>
      </div>
      <div className="split">
        <article className="card stack">
          <p className="eyebrow">Grocery list</p>
          {data.groceries.outstanding_count === 0 ? <p className="muted">Nothing left to buy.</p> : null}
          <ul className="plain">
            {data.groceries.items.map((item) => (
              <li key={item.id}>
                {item.name}{" "}
                <span className="muted">
                  {amount(item.quantity)} {item.unit}
                </span>
              </li>
            ))}
          </ul>
          <Link to="/groceries">Open the grocery list</Link>
        </article>
        <article className="card stack">
          <p className="eyebrow">Saved recipes</p>
          {data.saved_recipes.length === 0 ? <p className="muted">You have not saved a recipe yet.</p> : null}
          <ul className="plain">
            {data.saved_recipes.map((recipe) => (
              <li key={recipe.slug}>
                <Link to={`/recipes/${recipe.slug}`}>{recipe.title}</Link>
                <span className="muted"> · {recipe.nutrition_status}</span>
              </li>
            ))}
          </ul>
          <Link to="/recipes">Browse recipes</Link>
        </article>
      </div>
      <article className="card stack">
        <p className="eyebrow">Featured</p>
        {data.featured ? (
          <>
            <h2>{data.featured.title}</h2>
            <p>{data.featured.summary}</p>
            <p className="muted">{data.featured_reason}</p>
            <Link to={`/recipes/${data.featured.slug}`}>View the recipe</Link>
          </>
        ) : (
          <p className="muted">{data.featured_reason}</p>
        )}
      </article>
      <div className="shortcut-grid">
        <Link className="card" to="/recipes">
          Browse recipes
        </Link>
        <Link className="card" to="/groceries">
          Grocery list
        </Link>
        <Link className="card" to="/targets">
          Nutrition goals
        </Link>
        <Link className="card" to="/meals">
          Review meals
        </Link>
        <Link className="card" to="/today">
          Today’s nutrition
        </Link>
        <Link className="card" to="/suggestions">
          Suggestions
        </Link>
      </div>
    </section>
  );
}

import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "./api";

type RecipeCard = {
  slug: string;
  title: string;
  summary: string;
  base_servings: string;
  saved: boolean;
  nutrition_status: string;
};

type Ingredient = {
  id: number;
  label: string;
  quantity: string;
  unit: string;
  food_code: string | null;
  food_name: string | null;
  mapped: boolean;
  note: string;
};

type Nutrition = {
  status: string;
  servings: string;
  nutrients: Record<string, string | null> | null;
  missing: { label: string; reason: string }[];
  dataset_version: string | null;
};

type RecipeDetail = RecipeCard & {
  instructions: string;
  servings: string;
  source_name: string;
  source_note: string;
  license_note: string;
  ingredients: Ingredient[];
  nutrition: Nutrition;
};

type PlanEntry = {
  id: number;
  servings: string;
  recipe: { slug: string; title: string };
  nutrition: Nutrition;
};

type PlanDay = {
  date: string;
  slots: Record<string, PlanEntry[]>;
  nutrition: { status: string; nutrients: Record<string, string | null> | null; note: string };
};

type WeekPlan = { week_start: string; week_end: string; days: PlanDay[] };

type GroceryItem = {
  id: number;
  name: string;
  quantity: string;
  unit: string;
  purchased: boolean;
  origin: string;
  week_start: string | null;
};

const SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;

function messageFrom(err: unknown) {
  return err instanceof ApiError ? err.message : "Something went wrong.";
}

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function shiftDate(iso: string, days: number) {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  date.setDate(date.getDate() + days);
  const monthText = String(date.getMonth() + 1).padStart(2, "0");
  const dayText = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${monthText}-${dayText}`;
}

function nutritionSummary(nutrition: { status: string; nutrients: Record<string, string | null> | null; note?: string }) {
  if (nutrition.status === "empty") return nutrition.note || "Nothing planned.";
  if (nutrition.status !== "complete" || !nutrition.nutrients) {
    return "Nutrition is incomplete. A number is not shown because a verified calculation is missing.";
  }
  return `${amount(nutrition.nutrients.energy_kcal)} kcal · protein ${amount(nutrition.nutrients.protein_g)} g · carbs ${amount(nutrition.nutrients.carb_g)} g · fat ${amount(nutrition.nutrients.fat_g)} g`;
}

export function RecipesPage() {
  const [query, setQuery] = useState("");
  const [recipes, setRecipes] = useState<RecipeCard[] | null>(null);
  const [savedOnly, setSavedOnly] = useState(false);
  const [error, setError] = useState("");

  function load(text = query, saved = savedOnly) {
    const path = saved ? "/api/recipes/saved/" : `/api/recipes/?q=${encodeURIComponent(text)}`;
    return api<{ results: RecipeCard[] }>(path)
      .then((body) => setRecipes(body.results))
      .catch((err) => setError(messageFrom(err)));
  }

  useEffect(() => {
    load();
  }, [savedOnly]);

  function onSearch(event: FormEvent) {
    event.preventDefault();
    setError("");
    load(query, false);
    setSavedOnly(false);
  }

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <h1>Recipes</h1>
          <p className="muted">Curated recipes. Nutrition is calculated from verified foods when every ingredient matches.</p>
        </div>
      </header>
      <form className="card row-actions" onSubmit={onSearch}>
        <label>
          Search
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="rice" />
        </label>
        <button type="submit">Search</button>
        <button type="button" className="soft" onClick={() => setSavedOnly((current) => !current)}>
          {savedOnly ? "Show all recipes" : "Show saved recipes"}
        </button>
      </form>
      {error ? <p className="banner error">{error}</p> : null}
      {recipes === null ? <p className="muted">Loading recipes…</p> : null}
      {recipes && recipes.length === 0 ? <p className="banner">No recipes match.</p> : null}
      <div className="metric-grid">
        {recipes?.map((recipe) => (
          <article key={recipe.slug} className="card stack">
            <p className="eyebrow">{recipe.nutrition_status}</p>
            <h2>
              <Link to={`/recipes/${recipe.slug}`}>{recipe.title}</Link>
            </h2>
            <p className="muted">{recipe.summary}</p>
            <p className="muted">
              {amount(recipe.base_servings)} base servings{recipe.saved ? " · saved" : ""}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function RecipeDetailPage() {
  const { slug } = useParams();
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [servings, setServings] = useState("");
  const [planDate, setPlanDate] = useState("");
  const [slot, setSlot] = useState("dinner");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function load(nextServings?: string) {
    const query = nextServings ? `?servings=${encodeURIComponent(nextServings)}` : "";
    return api<RecipeDetail>(`/api/recipes/${slug}/${query}`)
      .then((body) => {
        setRecipe(body);
        setServings(body.servings);
        if (!planDate) setPlanDate(shiftDate(new Date().toLocaleDateString("en-CA"), 0));
      })
      .catch((err) => setError(messageFrom(err)));
  }

  useEffect(() => {
    setRecipe(null);
    load();
  }, [slug]);

  async function applyServings(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    await load(servings);
  }

  async function toggleSave() {
    if (!recipe) return;
    setError("");
    setNotice("");
    try {
      if (recipe.saved) {
        await api(`/api/recipes/${recipe.slug}/save/`, { method: "DELETE" });
      } else {
        await api(`/api/recipes/${recipe.slug}/save/`, { method: "POST" });
      }
      await load(servings);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function addToPlan(event: FormEvent) {
    event.preventDefault();
    if (!recipe) return;
    setError("");
    setNotice("");
    try {
      await api("/api/plans/entries/", {
        method: "POST",
        body: JSON.stringify({ date: planDate, slot, recipe_slug: recipe.slug, servings }),
      });
      setNotice("Added to the weekly planner. This does not log the meal as eaten.");
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  if (error && !recipe) return <p className="banner error">{error}</p>;
  if (!recipe) return <p className="muted">Loading recipe…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">{recipe.source_name}</p>
          <h1>{recipe.title}</h1>
        </div>
        <button type="button" className={recipe.saved ? "soft" : ""} onClick={toggleSave}>
          {recipe.saved ? "Remove from saved" : "Save recipe"}
        </button>
      </header>
      <p>{recipe.summary}</p>
      <p className="muted">{recipe.source_note}</p>
      <p className="muted">{recipe.license_note}</p>
      {error ? <p className="banner error">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}
      <form className="card row-actions" onSubmit={applyServings}>
        <label>
          Servings
          <input value={servings} onChange={(event) => setServings(event.target.value)} required />
        </label>
        <button type="submit">Update amounts</button>
      </form>
      <article className="card stack">
        <p className="eyebrow">Ingredients</p>
        <ul className="plain">
          {recipe.ingredients.map((item) => (
            <li key={item.id}>
              {amount(item.quantity)} {item.unit} {item.label}
              <span className="muted">
                {item.mapped ? ` · ${item.food_code}` : " · no verified food match"}
              </span>
            </li>
          ))}
        </ul>
      </article>
      <article className="card stack">
        <p className="eyebrow">Nutrition for {amount(recipe.nutrition.servings)} servings</p>
        <p>{nutritionSummary(recipe.nutrition)}</p>
        {recipe.nutrition.missing.map((item) => (
          <p key={item.label} className="muted">
            {item.label}: {item.reason}
          </p>
        ))}
        {recipe.nutrition.dataset_version ? (
          <p className="muted">Dataset {recipe.nutrition.dataset_version}</p>
        ) : null}
      </article>
      <article className="card stack">
        <p className="eyebrow">Method</p>
        <p>{recipe.instructions}</p>
      </article>
      <form className="card stack" onSubmit={addToPlan}>
        <p className="eyebrow">Add to the planner</p>
        <label>
          Date
          <input type="date" value={planDate} onChange={(event) => setPlanDate(event.target.value)} required />
        </label>
        <label>
          Meal
          <select value={slot} onChange={(event) => setSlot(event.target.value)}>
            {SLOTS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Add to week</button>
      </form>
    </section>
  );
}

export function PlannerPage() {
  const [week, setWeek] = useState("");
  const [plan, setPlan] = useState<WeekPlan | null>(null);
  const [recipes, setRecipes] = useState<RecipeCard[]>([]);
  const [recipeSlug, setRecipeSlug] = useState("");
  const [date, setDate] = useState("");
  const [slot, setSlot] = useState("dinner");
  const [servings, setServings] = useState("1");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function load(nextWeek = week) {
    const query = nextWeek ? `?week=${nextWeek}` : "";
    return api<WeekPlan>(`/api/plans/${query}`)
      .then((body) => {
        setPlan(body);
        setWeek(body.week_start);
        if (!date) setDate(body.week_start);
      })
      .catch((err) => setError(messageFrom(err)));
  }

  useEffect(() => {
    load();
    api<{ results: RecipeCard[] }>("/api/recipes/")
      .then((body) => {
        setRecipes(body.results);
        if (body.results[0]) setRecipeSlug(body.results[0].slug);
      })
      .catch((err) => setError(messageFrom(err)));
  }, []);

  async function addMeal(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api("/api/plans/entries/", {
        method: "POST",
        body: JSON.stringify({ date, slot, recipe_slug: recipeSlug, servings }),
      });
      setNotice("Saved to the planner. It is not logged as eaten.");
      await load(week);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function remove(id: number) {
    setError("");
    await api(`/api/plans/entries/${id}/`, { method: "DELETE" });
    await load(week);
  }

  async function changeServings(entry: PlanEntry, value: string) {
    setError("");
    try {
      await api(`/api/plans/entries/${entry.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ servings: value }),
      });
      await load(week);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function makeList() {
    setError("");
    setNotice("");
    try {
      const body = await api<{ message: string }>("/api/groceries/generate/", {
        method: "POST",
        body: JSON.stringify({ week }),
      });
      setNotice(body.message);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  if (error && !plan) return <p className="banner error">{error}</p>;
  if (!plan) return <p className="muted">Loading the week…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">
            {plan.week_start} to {plan.week_end}
          </p>
          <h1>Weekly planner</h1>
          <p className="muted">Plans stay separate from meals you log.</p>
        </div>
        <div className="row-actions">
          <button type="button" className="soft" onClick={() => load(shiftDate(plan.week_start, -7))}>
            Previous week
          </button>
          <button type="button" className="soft" onClick={() => load(shiftDate(plan.week_start, 7))}>
            Next week
          </button>
          <button type="button" onClick={makeList}>
            Grocery list for this week
          </button>
        </div>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}
      <form className="card stack" onSubmit={addMeal}>
        <p className="eyebrow">Add a recipe</p>
        <label>
          Recipe
          <select value={recipeSlug} onChange={(event) => setRecipeSlug(event.target.value)}>
            {recipes.map((recipe) => (
              <option key={recipe.slug} value={recipe.slug}>
                {recipe.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Date
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
        </label>
        <label>
          Meal
          <select value={slot} onChange={(event) => setSlot(event.target.value)}>
            {SLOTS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Servings
          <input value={servings} onChange={(event) => setServings(event.target.value)} required />
        </label>
        <button type="submit">Add to plan</button>
      </form>
      <div className="week-grid">
        {plan.days.map((day) => (
          <article key={day.date} className="card stack">
            <h2>{day.date.slice(5)}</h2>
            <p className="muted">{nutritionSummary(day.nutrition)}</p>
            {SLOTS.map((name) => (
              <div key={name}>
                <p className="eyebrow">{name}</p>
                {day.slots[name].length === 0 ? <p className="muted">Empty</p> : null}
                {day.slots[name].map((entry) => (
                  <div key={entry.id} className="stack">
                    <Link to={`/recipes/${entry.recipe.slug}`}>{entry.recipe.title}</Link>
                    <label>
                      Servings
                      <input
                        defaultValue={entry.servings}
                        onBlur={(event) => {
                          if (event.target.value !== entry.servings) changeServings(entry, event.target.value);
                        }}
                      />
                    </label>
                    <button type="button" className="soft" onClick={() => remove(entry.id)}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </article>
        ))}
      </div>
    </section>
  );
}

export function GroceriesPage() {
  const [items, setItems] = useState<GroceryItem[] | null>(null);
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("piece");
  const [week, setWeek] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  function load() {
    return api<{ items: GroceryItem[]; message?: string }>("/api/groceries/")
      .then((body) => setItems(body.items))
      .catch((err) => setError(messageFrom(err)));
  }

  useEffect(() => {
    load();
    api<WeekPlan>("/api/plans/")
      .then((body) => setWeek(body.week_start))
      .catch(() => setWeek(""));
  }, []);

  async function addItem(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      await api("/api/groceries/items/", {
        method: "POST",
        body: JSON.stringify({ name, quantity, unit }),
      });
      setName("");
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function toggle(item: GroceryItem) {
    setError("");
    try {
      await api(`/api/groceries/items/${item.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ purchased: !item.purchased }),
      });
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function saveEdit(item: GroceryItem, next: { name: string; quantity: string; unit: string }) {
    setError("");
    try {
      await api(`/api/groceries/items/${item.id}/`, {
        method: "PATCH",
        body: JSON.stringify(next),
      });
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function remove(item: GroceryItem) {
    setError("");
    await api(`/api/groceries/items/${item.id}/`, { method: "DELETE" });
    await load();
  }

  async function generate(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const body = await api<{ message: string; items: GroceryItem[] }>("/api/groceries/generate/", {
        method: "POST",
        body: JSON.stringify({ week }),
      });
      setItems(body.items);
      setNotice(body.message);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  const outstanding = (items ?? []).filter((item) => !item.purchased);
  const purchased = (items ?? []).filter((item) => item.purchased);

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <h1>Grocery list</h1>
          <p className="muted">Manual items stay when you refresh a week from the planner.</p>
        </div>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}
      <form className="card stack" onSubmit={addItem}>
        <p className="eyebrow">Add an item</p>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} required />
        </label>
        <label>
          Quantity
          <input value={quantity} onChange={(event) => setQuantity(event.target.value)} required />
        </label>
        <label>
          Unit
          <input value={unit} onChange={(event) => setUnit(event.target.value)} required />
        </label>
        <button type="submit">Add</button>
      </form>
      <form className="card row-actions" onSubmit={generate}>
        <label>
          Week
          <input type="date" value={week} onChange={(event) => setWeek(event.target.value)} required />
        </label>
        <button type="submit">Generate from planned meals</button>
      </form>
      {items === null ? <p className="muted">Loading the list…</p> : null}
      {items && items.length === 0 ? <p className="banner">The list is empty.</p> : null}
      <GroceryGroup title="Still to buy" items={outstanding} onToggle={toggle} onSave={saveEdit} onRemove={remove} />
      <GroceryGroup title="Purchased" items={purchased} onToggle={toggle} onSave={saveEdit} onRemove={remove} />
    </section>
  );
}

function GroceryGroup({
  title,
  items,
  onToggle,
  onSave,
  onRemove,
}: {
  title: string;
  items: GroceryItem[];
  onToggle: (item: GroceryItem) => void;
  onSave: (item: GroceryItem, next: { name: string; quantity: string; unit: string }) => void;
  onRemove: (item: GroceryItem) => void;
}) {
  if (items.length === 0) return null;
  return (
    <article className="card stack">
      <p className="eyebrow">{title}</p>
      <ul className="plain">
        {items.map((item) => (
          <GroceryRow key={item.id} item={item} onToggle={onToggle} onSave={onSave} onRemove={onRemove} />
        ))}
      </ul>
    </article>
  );
}

function GroceryRow({
  item,
  onToggle,
  onSave,
  onRemove,
}: {
  item: GroceryItem;
  onToggle: (item: GroceryItem) => void;
  onSave: (item: GroceryItem, next: { name: string; quantity: string; unit: string }) => void;
  onRemove: (item: GroceryItem) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(item.name);
  const [quantity, setQuantity] = useState(item.quantity);
  const [unit, setUnit] = useState(item.unit);

  return (
    <li className="stack">
      <label>
        <input type="checkbox" checked={item.purchased} onChange={() => onToggle(item)} /> {item.name}
      </label>
      <p className="muted">
        {amount(item.quantity)} {item.unit} · {item.origin}
        {item.week_start ? ` · week of ${item.week_start}` : ""}
      </p>
      {editing ? (
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            onSave(item, { name, quantity, unit });
            setEditing(false);
          }}
        >
          <input value={name} onChange={(event) => setName(event.target.value)} required />
          <input value={quantity} onChange={(event) => setQuantity(event.target.value)} required />
          <input value={unit} onChange={(event) => setUnit(event.target.value)} required />
          <button type="submit">Save changes</button>
        </form>
      ) : (
        <div className="row-actions">
          <button type="button" className="soft" onClick={() => setEditing(true)}>
            Edit
          </button>
          <button type="button" className="soft" onClick={() => onRemove(item)}>
            Remove
          </button>
        </div>
      )}
    </li>
  );
}

type Suggestion = {
  date: string;
  gaps: { nutrient: string; remaining: string | null; unit: string }[] | null;
  message: string;
  recipes: { slug: string; title: string; reason: string; nutrition: Nutrition }[];
};

export function SuggestionsPage() {
  const [data, setData] = useState<Suggestion | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Suggestion>("/api/suggestions/")
      .then(setData)
      .catch((err) => setError(messageFrom(err)));
  }, []);

  if (error) return <p className="banner error">{error}</p>;
  if (!data) return <p className="muted">Loading suggestions…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">{data.date}</p>
          <h1>Suggestions</h1>
        </div>
      </header>
      <p className="muted">{data.message}</p>
      {data.gaps ? (
        <article className="card stack">
          <p className="eyebrow">Remaining today</p>
          <ul className="plain">
            {data.gaps.map((gap) => (
              <li key={gap.nutrient}>
                {gap.nutrient.replaceAll("_", " ")} · {amount(gap.remaining)} {gap.unit}
              </li>
            ))}
          </ul>
        </article>
      ) : (
        <p className="banner">Set a nutrition target before gaps can be calculated.</p>
      )}
      {data.recipes.length === 0 ? <p className="banner">No recipe has a complete verified calculation.</p> : null}
      {data.recipes.map((recipe) => (
        <article key={recipe.slug} className="card stack">
          <h2>
            <Link to={`/recipes/${recipe.slug}`}>{recipe.title}</Link>
          </h2>
          <p>{recipe.reason}</p>
          <p className="muted">{nutritionSummary(recipe.nutrition)}</p>
        </article>
      ))}
    </section>
  );
}

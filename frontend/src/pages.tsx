import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";
import { CHAT_COPY, displayAssistantMessage } from "./chat-copy";
import { Logo } from "./logo";
import { useSession } from "./session";

export type Profile = {
  date_of_birth: string | null;
  sex: string;
  height_cm: string | null;
  weight_kg: string | null;
  activity_level: string;
  goal: string;
  allergies_status?: string;
  allergies?: string[];
  dislikes?: string[];
  diet_pattern?: string;
  preferred_cuisines?: string[];
  preferred_language?: string;
  appearance?: string;
  restrictions?: string[];
  likes?: string[];
  notes?: string;
  autoplay_replies?: boolean;
};

type Target = {
  id: number;
  source: string;
  calories: string;
  protein_g: string;
  carbohydrates_g: string;
  fat_g: string;
  fibre_g: string;
  effective_from: string;
  effective_until: string | null;
};

type Dashboard = {
  date: string;
  progress: {
    meal_count: number;
    consumed: Record<string, string | null>;
    remaining: Record<string, string | null> | null;
  };
  target: Target | null;
  streaks: { weekly: number; monthly: number; rule: string };
};

type MealItem = {
  id: number;
  food_code: string;
  food_name: string;
  quantity: string;
  unit: string;
  nutrition_snapshot: Record<string, string | null>;
};

type Meal = {
  id: number;
  timestamp: string;
  meal_type: string;
  items: MealItem[];
};

type FoodHit = {
  food_code: string;
  food_name: string;
  serving_unit: string;
};

type ChatReply = {
  status: string;
  conversation_id: number;
  message: string;
  meal_id: number | null;
};

const MACROS = [
  ["energy_kcal", "calories", "Calories", "kcal"],
  ["protein_g", "protein_g", "Protein", "g"],
  ["carb_g", "carbohydrates_g", "Carbs", "g"],
  ["fat_g", "fat_g", "Fat", "g"],
  ["fibre_g", "fibre_g", "Fibre", "g"],
] as const;

const MINERALS = [
  ["calcium_mg", "Calcium", "mg"],
  ["iron_mg", "Iron", "mg"],
  ["magnesium_mg", "Magnesium", "mg"],
  ["potassium_mg", "Potassium", "mg"],
  ["sodium_mg", "Sodium", "mg"],
  ["zinc_mg", "Zinc", "mg"],
] as const;

const VITAMINS = [
  ["vita_ug", "Vitamin A", "µg"],
  ["vitb1_mg", "Vitamin B1", "mg"],
  ["vitb2_mg", "Vitamin B2", "mg"],
  ["vitb3_mg", "Vitamin B3", "mg"],
  ["vitb6_mg", "Vitamin B6", "mg"],
  ["folate_ug", "Folate", "µg"],
  ["vitc_mg", "Vitamin C", "mg"],
  ["vitd2_ug", "Vitamin D2", "µg"],
  ["vitd3_ug", "Vitamin D3", "µg"],
  ["vite_mg", "Vitamin E", "mg"],
  ["vitk1_ug", "Vitamin K1", "µg"],
  ["vitk2_ug", "Vitamin K2", "µg"],
] as const;

function fillRatio(consumed: string | null | undefined, target: string | null | undefined) {
  if (consumed == null || target == null) return null;
  const eaten = Number(consumed);
  const goal = Number(target);
  if (!Number.isFinite(eaten) || !Number.isFinite(goal) || goal <= 0) return null;
  return Math.min(100, (eaten / goal) * 100);
}

export function profileComplete(profile: Profile) {
  return Boolean(
    profile.date_of_birth && profile.sex && profile.height_cm && profile.weight_kg && profile.activity_level && profile.goal,
  );
}

function showAmount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "unknown";
  return amount.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function messageFrom(err: unknown) {
  return err instanceof ApiError ? err.message : CHAT_COPY.genericError;
}

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/dashboard/")
      .then(setData)
      .catch((err) => setError(messageFrom(err)));
  }, []);

  if (error) return <p className="banner error">{error}</p>;
  if (!data) return <p className="muted">Loading today…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">{data.date}</p>
          <h1>Today</h1>
        </div>
        <div className="row-actions">
          <Link className="button" to="/log">
            Log a meal
          </Link>
          <Link className="soft" to="/suggestions">
            Suggestions
          </Link>
        </div>
      </header>
      {data.progress.meal_count === 0 ? <p className="banner">No meals saved yet today.</p> : null}
      <div className="metric-grid">
        {MACROS.map(([consumedKey, targetKey, label, unit], index) => {
          const consumed = data.progress.consumed[consumedKey];
          const target = data.target ? data.target[targetKey] : null;
          const remaining = data.progress.remaining ? data.progress.remaining[targetKey] : null;
          const width = fillRatio(consumed, target);
          return (
            <article key={consumedKey} className={index === 0 ? "card metric featured" : "card metric"}>
              <p className="eyebrow">{label}</p>
              <strong>{showAmount(consumed)}</strong>
              <p className="muted">
                {unit} eaten · target {target ? showAmount(target) : "not set"} · remaining {remaining ? showAmount(remaining) : "not set"}
              </p>
              {width == null ? null : (
                <div className={`bar is-${consumedKey}`} aria-hidden="true">
                  <span style={{ width: `${width}%` }} />
                </div>
              )}
            </article>
          );
        })}
      </div>
      <article className="card stack">
        <p className="eyebrow">Minerals</p>
        <div className="micro-grid">
          {MINERALS.map(([key, label, unit]) => (
            <p key={key}>
              <span className="muted">{label}</span>
              <strong className="stat">{showAmount(data.progress.consumed[key])}</strong>
              <span className="muted">{unit}</span>
            </p>
          ))}
        </div>
      </article>
      <article className="card stack">
        <p className="eyebrow">Vitamins</p>
        <div className="micro-grid">
          {VITAMINS.map(([key, label, unit]) => (
            <p key={key}>
              <span className="muted">{label}</span>
              <strong className="stat">{showAmount(data.progress.consumed[key])}</strong>
              <span className="muted">{unit}</span>
            </p>
          ))}
        </div>
      </article>
      <div className="split">
        <article className="card">
          <p className="eyebrow">Streaks</p>
          <p>
            {data.streaks.weekly} weekly · {data.streaks.monthly} monthly
          </p>
          <p className="muted">{data.streaks.rule}</p>
        </article>
        <article className="card">
          <p className="eyebrow">Meals today</p>
          <p>{data.progress.meal_count}</p>
          <Link to="/meals">Open the meal list</Link>
        </article>
      </div>
    </section>
  );
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const { logout } = useSession();
  const [form, setForm] = useState({
    date_of_birth: "",
    sex: "",
    height_cm: "",
    weight_kg: "",
    activity_level: "",
    goal: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api<Profile>("/api/profile/")
      .then((profile) => {
        setForm({
          date_of_birth: profile.date_of_birth ?? "",
          sex: profile.sex || "",
          height_cm: profile.height_cm ?? "",
          weight_kg: profile.weight_kg ?? "",
          activity_level: profile.activity_level || "",
          goal: profile.goal || "",
        });
      })
      .catch((err) => setError(messageFrom(err)))
      .finally(() => setReady(true));
  }, []);

  function update(name: string, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/profile/", { method: "PUT", body: JSON.stringify(form) });
      navigate("/profile");
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card narrow stack">
      <h1>Your profile</h1>
      <p className="muted">Targets are calculated from these details. They are not stored until you accept them.</p>
      {!ready ? <p className="muted">Loading profile…</p> : null}
      {error ? <p className="banner error">{error}</p> : null}
      <form onSubmit={onSubmit} className="stack">
        <label>
          Date of birth
          <input type="date" value={form.date_of_birth} onChange={(event) => update("date_of_birth", event.target.value)} required />
        </label>
        <label>
          Sex
          <select value={form.sex} onChange={(event) => update("sex", event.target.value)} required>
            <option value="">Select</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
        </label>
        <label>
          Height (cm)
          <input value={form.height_cm} onChange={(event) => update("height_cm", event.target.value)} required />
        </label>
        <label>
          Weight (kg)
          <input value={form.weight_kg} onChange={(event) => update("weight_kg", event.target.value)} required />
        </label>
        <label>
          Activity
          <select value={form.activity_level} onChange={(event) => update("activity_level", event.target.value)} required>
            <option value="">Select</option>
            <option value="sedentary">Sedentary</option>
            <option value="lightly_active">Lightly active</option>
            <option value="moderately_active">Moderately active</option>
            <option value="very_active">Very active</option>
          </select>
        </label>
        <label>
          Goal
          <select value={form.goal} onChange={(event) => update("goal", event.target.value)} required>
            <option value="">Select</option>
            <option value="maintain">Maintain weight</option>
            <option value="lose">Lose weight</option>
            <option value="gain">Gain weight</option>
          </select>
        </label>
        <button type="submit" disabled={busy || !ready}>
          {busy ? "Saving…" : "Save profile"}
        </button>
      </form>
      <button
        type="button"
        className="soft"
        onClick={() => {
          void logout();
        }}
      >
        Log out
      </button>
    </section>
  );
}

export function TargetsPage() {
  const [current, setCurrent] = useState<Target | null | undefined>(undefined);
  const [suggestion, setSuggestion] = useState<Record<string, string> | null>(null);
  const [history, setHistory] = useState<Target[]>([]);
  const [custom, setCustom] = useState({ calories: "", protein_g: "", carbohydrates_g: "", fat_g: "", fibre_g: "" });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function reload() {
    const [now, past] = await Promise.all([
      api<{ target: Target | null }>("/api/targets/"),
      api<{ results: Target[] }>("/api/targets/history/"),
    ]);
    setCurrent(now.target);
    setHistory(past.results);
  }

  useEffect(() => {
    reload().catch((err) => setError(messageFrom(err)));
  }, []);

  async function suggest() {
    setError("");
    setNotice("");
    try {
      const body = await api<{ suggestion: Record<string, string>; saved: boolean }>("/api/targets/suggest/", {
        method: "POST",
        body: "{}",
      });
      setSuggestion(body.suggestion);
      setNotice(body.saved ? "" : "This suggestion is not saved yet.");
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function accept() {
    setError("");
    try {
      await api("/api/targets/accept-suggestion/", { method: "POST", body: "{}" });
      setSuggestion(null);
      setNotice("Suggestion saved as your current target.");
      await reload();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function customize(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/targets/customize/", { method: "POST", body: JSON.stringify(custom) });
      setNotice("Your numbers are now the current target.");
      await reload();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  return (
    <section className="stack">
      <header className="page-head">
        <h1>Targets</h1>
        <button type="button" onClick={suggest}>
          Suggest from profile
        </button>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}
      <article className="card">
        <p className="eyebrow">Current</p>
        {current === undefined ? <p className="muted">Loading…</p> : null}
        {current === null ? <p>No target saved.</p> : null}
        {current ? <TargetLines target={current} /> : null}
      </article>
      {suggestion ? (
        <article className="card stack">
          <p className="eyebrow">Suggestion</p>
          <p>
            {showAmount(suggestion.calories)} kcal · protein {showAmount(suggestion.protein_g)} g · carbs{" "}
            {showAmount(suggestion.carbohydrates_g)} g · fat {showAmount(suggestion.fat_g)} g · fibre{" "}
            {showAmount(suggestion.fibre_g)} g
          </p>
          <button type="button" onClick={accept}>
            Accept suggestion
          </button>
        </article>
      ) : null}
      <form className="card stack" onSubmit={customize}>
        <p className="eyebrow">Use your own numbers</p>
        {Object.keys(custom).map((name) => (
          <label key={name}>
            {name.replaceAll("_", " ")}
            <input value={custom[name as keyof typeof custom]} onChange={(event) => setCustom({ ...custom, [name]: event.target.value })} required />
          </label>
        ))}
        <button type="submit">Save my numbers</button>
      </form>
      <article className="card">
        <p className="eyebrow">History</p>
        {history.length === 0 ? <p className="muted">No earlier targets.</p> : null}
        <ul className="plain">
          {history.map((row) => (
            <li key={row.id}>
              {row.source} · {showAmount(row.calories)} kcal · from {row.effective_from}
              {row.effective_until ? ` until ${row.effective_until}` : " · open"}
            </li>
          ))}
        </ul>
      </article>
    </section>
  );
}

function TargetLines({ target }: { target: Target }) {
  return (
    <p>
      {target.source} · {showAmount(target.calories)} kcal · protein {showAmount(target.protein_g)} g · carbs{" "}
      {showAmount(target.carbohydrates_g)} g · fat {showAmount(target.fat_g)} g · fibre {showAmount(target.fibre_g)} g
    </p>
  );
}

export function LogFoodPage() {
  return <MealsPage mode="log" />;
}

export function LogMealPage() {
  return (
    <div className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">Today’s meals</p>
          <h1>Log a meal</h1>
          <p className="muted">Describe what you ate, or search the verified food list and save the amount yourself.</p>
        </div>
      </header>
      <ChatPage />
      <LogFoodPage />
    </div>
  );
}

export function MealsPage({ mode = "history" }: { mode?: "log" | "history" }) {
  const [meals, setMeals] = useState<Meal[] | null>(null);
  const [day, setDay] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<FoodHit[] | null>(null);
  const [picked, setPicked] = useState<FoodHit | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("g");
  const [mealType, setMealType] = useState("breakfast");
  const [error, setError] = useState("");

  async function load(selected = day) {
    const body = await api<{ results: Meal[] }>(`/api/meals/?date=${selected}`);
    setMeals(body.results);
  }

  useEffect(() => {
    if (!day) {
      api<Dashboard>("/api/dashboard/")
        .then((dashboard) => setDay(dashboard.date))
        .catch((err) => setError(messageFrom(err)));
      return;
    }
    load(day).catch((err) => setError(messageFrom(err)));
  }, [day]);

  async function search(event: FormEvent) {
    event.preventDefault();
    setError("");
    setPicked(null);
    try {
      const body = await api<{ results: FoodHit[] }>(`/api/foods/search/?q=${encodeURIComponent(query)}`);
      setHits(body.results);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function saveMeal(event: FormEvent) {
    event.preventDefault();
    if (!picked) return;
    setError("");
    try {
      await api("/api/meals/", {
        method: "POST",
        body: JSON.stringify({
          meal_type: mealType,
          items: [{ food_code: picked.food_code, quantity, unit, input_source: "manual" }],
        }),
      });
      setPicked(null);
      setHits(null);
      setQuery("");
      await load(day);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          {mode === "log" ? <h2>Search a verified food</h2> : <h1>Meal history</h1>}
          <p className="muted">
            {mode === "log" ? (
              "Choose a food, a quantity, and a unit the dataset supports."
            ) : (
              <Link to="/log">Log a Meal</Link>
            )}
          </p>
        </div>
        <label>
          Date
          <input type="date" value={day} onChange={(event) => setDay(event.target.value)} />
        </label>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {mode === "log" ? (
      <>
      <form className="card stack" onSubmit={search}>
        <label>
          Find a verified food
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="idli" />
        </label>
        <button type="submit">Search</button>
        {hits === null ? <p className="muted">Search results appear here.</p> : null}
        {hits && hits.length === 0 ? <p className="banner">No verified food matches that search.</p> : null}
        <ul className="plain">
          {hits?.map((food) => (
            <li key={food.food_code}>
              <button
                type="button"
                className="linkish"
                onClick={() => {
                  setPicked(food);
                  setUnit(food.serving_unit || "g");
                }}
              >
                {food.food_name}
              </button>
              <span className="muted"> {food.food_code}{food.serving_unit ? ` · serving: ${food.serving_unit}` : ""}</span>
            </li>
          ))}
        </ul>
      </form>
      {picked ? (
        <form className="card stack" onSubmit={saveMeal}>
          <p>
            {picked.food_name} <span className="muted">{picked.food_code}</span>
          </p>
          <label>
            Quantity
            <input value={quantity} onChange={(event) => setQuantity(event.target.value)} required />
          </label>
          <label>
            Unit
            <input value={unit} onChange={(event) => setUnit(event.target.value)} required />
          </label>
          <label>
            Meal
            <select value={mealType} onChange={(event) => setMealType(event.target.value)}>
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="dinner">Dinner</option>
              <option value="snack">Snack</option>
              <option value="unspecified">Unspecified</option>
            </select>
          </label>
          <button type="submit">Save meal</button>
        </form>
      ) : null}
      </>
      ) : null}
      {meals === null ? <p className="muted">Loading meals…</p> : null}
      {meals && meals.length === 0 ? <p className="banner">No meals saved for {day}.</p> : null}
      <ul className="plain">
        {(meals ?? []).map((meal) => (
          <li key={meal.id} className="card">
            <Link to={`/meals/${meal.id}`}>
              {meal.meal_type} · {new Date(meal.timestamp).toLocaleString()}
            </Link>
            <p className="muted">
              {meal.items.map((item) => `${item.quantity} ${item.unit} ${item.food_name}`).join(", ")}
              {meal.items[0] ? ` · ${displayKcal(meal.items[0].nutrition_snapshot.energy_kcal)} kcal` : ""}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function MealDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [meal, setMeal] = useState<Meal | null>(null);
  const [mealType, setMealType] = useState("breakfast");
  const [rows, setRows] = useState<Array<{ food_code: string; quantity: string; unit: string }>>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Meal>(`/api/meals/${id}/`)
      .then((loaded) => {
        setMeal(loaded);
        setMealType(loaded.meal_type);
        setRows(loaded.items.map((item) => ({ food_code: item.food_code, quantity: item.quantity, unit: item.unit })));
      })
      .catch((err) => setError(messageFrom(err)));
  }, [id]);

  async function remove() {
    await api(`/api/meals/${id}/`, { method: "DELETE" });
    navigate("/meals");
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await api<Meal>(`/api/meals/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({
          meal_type: mealType,
          items: rows.map((row) => ({ ...row, input_source: "manual" })),
        }),
      });
      setMeal(updated);
      setNotice("Meal updated from the verified dataset.");
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (error && !meal) return <p className="banner error">{error}</p>;
  if (!meal) return <p className="muted">Loading meal…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">{new Date(meal.timestamp).toLocaleString()}</p>
          <h1>{meal.meal_type}</h1>
        </div>
        <button type="button" className="soft" onClick={remove}>
          Delete meal
        </button>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}
      <form className="stack" onSubmit={save}>
        <label>
          Meal type
          <select value={mealType} onChange={(event) => setMealType(event.target.value)}>
            <option value="breakfast">Breakfast</option>
            <option value="lunch">Lunch</option>
            <option value="dinner">Dinner</option>
            <option value="snack">Snack</option>
            <option value="unspecified">Unspecified</option>
          </select>
        </label>
        {meal.items.map((item, index) => (
          <article key={item.id} className="card stack">
            <h2>
              {item.food_name}
            </h2>
            <p className="muted">{item.food_code}</p>
            <label>
              Quantity
              <input
                value={rows[index]?.quantity ?? ""}
                onChange={(event) =>
                  setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, quantity: event.target.value } : row)))
                }
                required
              />
            </label>
            <label>
              Unit
              <input
                value={rows[index]?.unit ?? ""}
                onChange={(event) =>
                  setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, unit: event.target.value } : row)))
                }
                required
              />
            </label>
            <p>Energy {displayKcal(item.nutrition_snapshot.energy_kcal)} kcal</p>
            <p>Protein {showAmount(item.nutrition_snapshot.protein_g)} g</p>
            <p>Carbs {showAmount(item.nutrition_snapshot.carb_g)} g</p>
            <p>Fat {showAmount(item.nutrition_snapshot.fat_g)} g</p>
            <p>Fibre {showAmount(item.nutrition_snapshot.fibre_g)} g</p>
          </article>
        ))}
        <button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save changes"}
        </button>
      </form>
    </section>
  );
}

type SpeechResult = { results: Array<Array<{ transcript: string }>> };

export function ChatPage() {
  const [text, setText] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Array<{ role: string; content: string; status?: string }>>([]);
  const [historyReady, setHistoryReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sendingRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    api<{ results: Array<{ id: number }> }>("/api/conversations/")
      .then(async (list) => {
        const latest = list.results[0];
        if (!latest || cancelled) return;
        const detail = await api<{ id: number; messages: Array<{ role: string; content: string }> }>(
          `/api/conversations/${latest.id}/`,
        );
        if (cancelled) return;
        setConversationId(detail.id);
        setTurns(detail.messages.map((message) => ({ role: message.role, content: message.content })));
      })
      .catch((err) => {
        if (!cancelled) setError(messageFrom(err));
      })
      .finally(() => {
        if (!cancelled) setHistoryReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function send(path: string, body: Record<string, unknown>, spoken: string) {
    if (sendingRef.current) return;
    sendingRef.current = true;
    setBusy(true);
    setError("");
    setTurns((current) => {
      const last = current[current.length - 1];
      if (last?.role === "user" && last.content === spoken) return current;
      return [...current, { role: "user", content: spoken }];
    });
    try {
      const reply = await api<ChatReply>(path, {
        method: "POST",
        body: JSON.stringify({ ...body, conversation_id: conversationId }),
      });
      setConversationId(reply.conversation_id);
      setTurns((current) => {
        const content = displayAssistantMessage(reply.status, reply.message);
        const last = current[current.length - 1];
        if (last?.role === "assistant" && last.content === content) return current;
        return [...current, { role: "assistant", content }];
      });
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      sendingRef.current = false;
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message || !historyReady || sendingRef.current) return;
    setText("");
    await send("/api/agent/chat/", { message }, message);
  }

  function listen() {
    const recognitionWindow = window as Window & {
      SpeechRecognition?: new () => SpeechRecognizer;
      webkitSpeechRecognition?: new () => SpeechRecognizer;
    };
    const Ctor = recognitionWindow.SpeechRecognition ?? recognitionWindow.webkitSpeechRecognition;
    if (!Ctor) {
      setError("This browser has no speech recognizer. Type the meal instead.");
      return;
    }
    const recognizer = new Ctor();
    recognizer.lang = "en-IN";
    recognizer.onresult = (event: SpeechResult) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      if (transcript) void send("/api/agent/voice/", { transcript }, transcript);
    };
    recognizer.onerror = () => setError("Speech recognition stopped before a transcript was ready.");
    recognizer.start();
  }

  async function imageUnavailable() {
    setBusy(true);
    setError("");
    try {
      await api("/api/agent/image/", { method: "POST", body: "{}" });
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card chat-panel">
      <header className="chat-head">
        <div className="brand">
          <Logo />
          <p className="brand-name">{CHAT_COPY.title}</p>
        </div>
        <button
          type="button"
          className="soft"
          onClick={() => {
            setConversationId(null);
            setTurns([]);
            setError("");
          }}
        >
          New conversation
        </button>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      <p className="muted">{CHAT_COPY.intro}</p>
      <div className="chat-log" aria-live="polite">
        {!historyReady ? <p className="muted">{CHAT_COPY.loading}</p> : null}
        {historyReady && turns.length === 0 ? <p className="muted">{CHAT_COPY.empty}</p> : null}
        {turns.map((turn, index) => (
          <article key={`${turn.role}-${index}`} className={`bubble ${turn.role}`}>
            <p className="eyebrow">{turn.role === "user" ? "You" : "Swasthya"}</p>
            <p>{turn.content}</p>
          </article>
        ))}
        {busy ? <p className="muted">{CHAT_COPY.busy}</p> : null}
      </div>
      <form className="composer" onSubmit={onSubmit}>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder={CHAT_COPY.placeholder} />
        <button type="submit" disabled={busy}>
          Send
        </button>
        <button type="button" className="soft" onClick={listen} disabled={busy}>
          Speak
        </button>
        <button type="button" className="soft" onClick={imageUnavailable} disabled={busy}>
          Image
        </button>
      </form>
    </section>
  );
}

type SpeechRecognizer = {
  lang: string;
  start: () => void;
  onresult: ((event: SpeechResult) => void) | null;
  onerror: (() => void) | null;
};

export function SettingsPage() {
  const { user, logout } = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Profile>("/api/profile/")
      .then(setProfile)
      .catch((err) => setError(messageFrom(err)));
  }, []);

  async function onLogout() {
    await logout();
  }

  return (
    <section className="card stack narrow">
      <h1>Settings</h1>
      <p>
        {user?.name} · {user?.email}
      </p>
      {error ? <p className="banner error">{error}</p> : null}
      {profile ? (
        <p className="muted">
          {profile.sex || "Sex not set"} · {profile.height_cm ?? "unknown"} cm · {profile.weight_kg ?? "unknown"} kg ·{" "}
          {profile.activity_level || "activity not set"} · {profile.goal || "goal not set"}
        </p>
      ) : (
        <p className="muted">Loading profile…</p>
      )}
      <p className="muted">
        The sign-in tokens stay in this browser tab’s session storage. That is temporary and is not the final storage design.
      </p>
      <Link to="/profile">Edit profile</Link>
      <button type="button" onClick={onLogout}>
        Log out
      </button>
    </section>
  );
}

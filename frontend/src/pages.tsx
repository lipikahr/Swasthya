import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { useSession } from "./session";

export type Profile = {
  date_of_birth: string | null;
  sex: string;
  height_cm: string | null;
  weight_kg: string | null;
  activity_level: string;
  goal: string;
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
  ["energy_kcal", "calories", "Calories"],
  ["protein_g", "protein_g", "Protein"],
  ["carb_g", "carbohydrates_g", "Carbs"],
  ["fat_g", "fat_g", "Fat"],
  ["fibre_g", "fibre_g", "Fibre"],
] as const;

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
  return err instanceof ApiError ? err.message : "Something went wrong.";
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
        <Link className="button" to="/chat">
          Log a meal
        </Link>
      </header>
      {data.progress.meal_count === 0 ? <p className="banner">No meals saved yet today.</p> : null}
      <div className="metric-grid">
        {MACROS.map(([consumedKey, targetKey, label]) => (
          <article key={consumedKey} className="card metric">
            <p className="eyebrow">{label}</p>
            <strong>{showAmount(data.progress.consumed[consumedKey])}</strong>
            <p className="muted">
              Target {data.target ? showAmount(data.target[targetKey]) : "not set"} · Remaining{" "}
              {data.progress.remaining ? showAmount(data.progress.remaining[targetKey]) : "not set"}
            </p>
          </article>
        ))}
      </div>
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
  const [form, setForm] = useState({
    date_of_birth: "",
    sex: "female",
    height_cm: "",
    weight_kg: "",
    activity_level: "sedentary",
    goal: "maintain",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(name: string, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/profile/", { method: "PUT", body: JSON.stringify(form) });
      navigate("/");
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
      {error ? <p className="banner error">{error}</p> : null}
      <form onSubmit={onSubmit} className="stack">
        <label>
          Date of birth
          <input type="date" value={form.date_of_birth} onChange={(event) => update("date_of_birth", event.target.value)} required />
        </label>
        <label>
          Sex
          <select value={form.sex} onChange={(event) => update("sex", event.target.value)}>
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
          <select value={form.activity_level} onChange={(event) => update("activity_level", event.target.value)}>
            <option value="sedentary">Sedentary</option>
            <option value="lightly_active">Lightly active</option>
            <option value="moderately_active">Moderately active</option>
            <option value="very_active">Very active</option>
          </select>
        </label>
        <label>
          Goal
          <select value={form.goal} onChange={(event) => update("goal", event.target.value)}>
            <option value="maintain">Maintain</option>
            <option value="lose">Lose weight</option>
            <option value="gain">Gain weight</option>
          </select>
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save profile"}
        </button>
      </form>
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

export function MealsPage() {
  const [meals, setMeals] = useState<Meal[] | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<FoodHit[]>([]);
  const [picked, setPicked] = useState<FoodHit | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [unit, setUnit] = useState("g");
  const [mealType, setMealType] = useState("breakfast");
  const [error, setError] = useState("");

  async function load() {
    const today = new Date().toISOString().slice(0, 10);
    const body = await api<{ results: Meal[] }>(`/api/meals/?date=${today}`);
    setMeals(body.results);
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, []);

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
      setHits([]);
      setQuery("");
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  return (
    <section className="stack">
      <header className="page-head">
        <h1>Meals</h1>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      <form className="card stack" onSubmit={search}>
        <label>
          Find a verified food
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="idli" />
        </label>
        <button type="submit">Search</button>
        {hits.length === 0 ? <p className="muted">Search results appear here.</p> : null}
        <ul className="plain">
          {hits.map((food) => (
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
      {meals === null ? <p className="muted">Loading meals…</p> : null}
      {meals && meals.length === 0 ? <p className="banner">Nothing saved for today.</p> : null}
      <ul className="plain">
        {(meals ?? []).map((meal) => (
          <li key={meal.id} className="card">
            <Link to={`/meals/${meal.id}`}>
              {meal.meal_type} · {new Date(meal.timestamp).toLocaleTimeString()}
            </Link>
            <p className="muted">{meal.items.map((item) => item.food_name).join(", ")}</p>
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
  const [error, setError] = useState("");

  useEffect(() => {
    api<Meal>(`/api/meals/${id}/`)
      .then(setMeal)
      .catch((err) => setError(messageFrom(err)));
  }, [id]);

  async function remove() {
    await api(`/api/meals/${id}/`, { method: "DELETE" });
    navigate("/meals");
  }

  if (error) return <p className="banner error">{error}</p>;
  if (!meal) return <p className="muted">Loading meal…</p>;

  return (
    <section className="stack">
      <header className="page-head">
        <h1>{meal.meal_type}</h1>
        <button type="button" onClick={remove}>
          Delete meal
        </button>
      </header>
      {meal.items.map((item) => (
        <article key={item.id} className="card">
          <h2>
            {item.quantity} {item.unit} {item.food_name}
          </h2>
          <p className="muted">{item.food_code}</p>
          <p>Energy {showAmount(item.nutrition_snapshot.energy_kcal)} kcal</p>
          <p>Protein {showAmount(item.nutrition_snapshot.protein_g)} g</p>
          <p>Carbs {showAmount(item.nutrition_snapshot.carb_g)} g</p>
          <p>Fat {showAmount(item.nutrition_snapshot.fat_g)} g</p>
          <p>Fibre {showAmount(item.nutrition_snapshot.fibre_g)} g</p>
        </article>
      ))}
    </section>
  );
}

type SpeechResult = { results: Array<Array<{ transcript: string }>> };

export function ChatPage() {
  const [text, setText] = useState("");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Array<{ role: string; content: string; status?: string }>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(path: string, body: Record<string, unknown>, spoken: string) {
    setBusy(true);
    setError("");
    setTurns((current) => [...current, { role: "user", content: spoken }]);
    try {
      const reply = await api<ChatReply>(path, {
        method: "POST",
        body: JSON.stringify({ ...body, conversation_id: conversationId }),
      });
      setConversationId(reply.conversation_id);
      setTurns((current) => [...current, { role: "assistant", content: reply.message, status: reply.status }]);
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message) return;
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
    <section className="stack">
      <header className="page-head">
        <div>
          <h1>Log in words</h1>
          <p className="muted">A meal is saved only after the reply says SUCCESS.</p>
        </div>
      </header>
      {error ? <p className="banner error">{error}</p> : null}
      {turns.length === 0 ? <p className="banner">Try “I ate 2 idlis for breakfast”.</p> : null}
      <ol className="plain">
        {turns.map((turn, index) => (
          <li key={`${turn.role}-${index}`} className={`card turn ${turn.role}`}>
            <p className="eyebrow">{turn.role}{turn.status ? ` · ${turn.status}` : ""}</p>
            <p>{turn.content}</p>
          </li>
        ))}
      </ol>
      {busy ? <p className="muted">Working…</p> : null}
      <form className="composer" onSubmit={onSubmit}>
        <input value={text} onChange={(event) => setText(event.target.value)} placeholder="What did you eat?" />
        <button type="submit" disabled={busy}>
          Send
        </button>
        <button type="button" onClick={listen} disabled={busy}>
          Speak
        </button>
        <button type="button" onClick={imageUnavailable} disabled={busy}>
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
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <section className="card stack narrow">
      <h1>Settings</h1>
      <p>
        {user?.name} · {user?.email}
      </p>
      <p className="muted">
        The sign-in tokens stay in this browser tab’s session storage. That is temporary and is not the final storage design.
      </p>
      <Link to="/onboarding">Edit profile</Link>
      <button type="button" onClick={onLogout}>
        Log out
      </button>
    </section>
  );
}

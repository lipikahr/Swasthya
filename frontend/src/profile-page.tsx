import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "./api";
import { SUPPORTED_LANGUAGES } from "./languages";
import { profileComplete, type Profile } from "./pages";
import { useSession } from "./session";

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

const ACTIVITIES = [
  ["sedentary", "Sedentary"],
  ["lightly_active", "Lightly active"],
  ["moderately_active", "Moderately active"],
  ["very_active", "Very active"],
] as const;

const GOALS = [
  ["maintain", "Maintain weight"],
  ["lose", "Lose weight"],
  ["gain", "Gain weight"],
] as const;

const TARGET_FIELDS = [
  ["calories", "Calories", "kcal"],
  ["protein_g", "Protein", "g"],
  ["carbohydrates_g", "Carbs", "g"],
  ["fat_g", "Fat", "g"],
  ["fibre_g", "Fibre", "g"],
] as const;

function messageFrom(err: unknown) {
  return err instanceof ApiError ? err.message : "Something went wrong.";
}

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function labelFor(options: readonly (readonly [string, string])[], value: string) {
  return options.find(([code]) => code === value)?.[1] ?? "Not set";
}

function sourceLabel(source: string) {
  if (source === "system_suggested") return "System suggested";
  if (source === "user_customized") return "Your numbers";
  return source;
}

const ALLERGY_CHOICES = ["milk", "egg", "peanut", "tree nut", "wheat", "soy", "fish", "shellfish", "sesame", "mustard"];
const CUISINE_CHOICES = ["South Indian", "North Indian", "Gujarati", "Bengali", "Punjabi", "Maharashtrian"];

const emptyForm = {
  date_of_birth: "",
  sex: "",
  height_cm: "",
  weight_kg: "",
  activity_level: "",
  goal: "",
};

const emptyPrefs = {
  allergies_status: "",
  allergies: [] as string[],
  customAllergy: "",
  dislikes: "",
  diet_pattern: "",
  preferred_cuisines: [] as string[],
  preferred_language: "en",
};

export function ProfilePage() {
  const { user, logout } = useSession();
  const [form, setForm] = useState(emptyForm);
  const [prefs, setPrefs] = useState(emptyPrefs);
  const [editing, setEditing] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [current, setCurrent] = useState<Target | null | undefined>(undefined);
  const [history, setHistory] = useState<Target[]>([]);
  const [suggestion, setSuggestion] = useState<Record<string, string> | null>(null);
  const [replaceCustom, setReplaceCustom] = useState(false);
  const [custom, setCustom] = useState({ calories: "", protein_g: "", carbohydrates_g: "", fat_g: "", fibre_g: "" });

  async function loadTargets() {
    const [now, past] = await Promise.all([
      api<{ target: Target | null }>("/api/targets/"),
      api<{ results: Target[] }>("/api/targets/history/"),
    ]);
    setCurrent(now.target);
    setHistory(past.results);
  }

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
        setPrefs({
          allergies_status: profile.allergies_status ?? "",
          allergies: profile.allergies ?? [],
          customAllergy: "",
          dislikes: (profile.dislikes ?? []).join(", "),
          diet_pattern: profile.diet_pattern ?? "",
          preferred_cuisines: profile.preferred_cuisines ?? [],
          preferred_language: profile.preferred_language || "en",
        });
        setEditing(!profileComplete(profile));
      })
      .catch((err) => setError(messageFrom(err)))
      .finally(() => setReady(true));
    loadTargets().catch((err) => setError(messageFrom(err)));
  }, []);

  function update(name: string, value: string) {
    setForm((currentForm) => ({ ...currentForm, [name]: value }));
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!form.sex || !form.activity_level || !form.goal) {
      setError("Choose sex, activity, and a goal before saving. Nothing is assumed.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api("/api/profile/", { method: "PUT", body: JSON.stringify(form) });
      setEditing(false);
      setNotice("Profile saved.");
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  async function suggest() {
    setError("");
    setNotice("");
    setReplaceCustom(false);
    try {
      const body = await api<{ suggestion: Record<string, string>; saved: boolean }>("/api/targets/suggest/", {
        method: "POST",
        body: "{}",
      });
      setSuggestion(body.suggestion);
      setNotice("This suggestion is not saved. Accept it only if you want it to become the active target.");
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function accept() {
    if (current?.source === "user_customized" && !replaceCustom) {
      setError("Your current target was entered by you. Confirm that replacing it is intentional. The previous target stays in history.");
      return;
    }
    setError("");
    try {
      await api("/api/targets/accept-suggestion/", { method: "POST", body: "{}" });
      setSuggestion(null);
      setReplaceCustom(false);
      setNotice("The suggestion is now the active target. The previous target remains in history.");
      await loadTargets();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function saveCustom(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/targets/customize/", { method: "POST", body: JSON.stringify(custom) });
      setNotice("Your numbers are now the active target. The previous target remains in history.");
      await loadTargets();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  return (
    <div className="profile-layout">
      <aside className="card side-links">
        <Link className="active" to="/onboarding">Profile</Link>
        <Link to="/coach">Log a Meal</Link>
        <Link to="/today">Today</Link>
        <button
          type="button"
          onClick={() => {
            void logout();
          }}
        >
          Log out
        </button>
      </aside>
      <div className="stack">
        <header className="page-head">
          <div>
            <p className="eyebrow">Profile</p>
            <h1>Your profile</h1>
            <p className="muted">{user?.name} · {user?.email}</p>
          </div>
          {!editing && (
            <button type="button" onClick={() => setEditing(true)}>Edit Profile</button>
          )}
        </header>
        {error ? <p className="banner error" role="alert">{error}</p> : null}
        {notice ? <p className="banner" role="status">{notice}</p> : null}
        {!ready ? <p className="muted">Loading profile…</p> : null}
        <form className="card stack" onSubmit={saveProfile}>
          <p className="muted">The name and email come from the account. This form saves the body details used for targets.</p>
          <div className="field-grid">
            <label>Date of birth<input type="date" value={form.date_of_birth} disabled={!editing} required onChange={(event) => update("date_of_birth", event.target.value)} /></label>
            <label>
              Sex
              <select value={form.sex} disabled={!editing} required onChange={(event) => update("sex", event.target.value)}>
                <option value="">Select</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </label>
            <label>Height (cm)<input inputMode="decimal" value={form.height_cm} disabled={!editing} required onChange={(event) => update("height_cm", event.target.value)} /></label>
            <label>Weight (kg)<input inputMode="decimal" value={form.weight_kg} disabled={!editing} required onChange={(event) => update("weight_kg", event.target.value)} /></label>
            <label>
              Activity level
              <select value={form.activity_level} disabled={!editing} required onChange={(event) => update("activity_level", event.target.value)}>
                <option value="">Select</option>
                {ACTIVITIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label>
              Goal
              <select value={form.goal} disabled={!editing} required onChange={(event) => update("goal", event.target.value)}>
                <option value="">Select</option>
                {GOALS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
          </div>
          {!editing && (
            <p className="muted">
              {labelFor([["female", "Female"], ["male", "Male"]], form.sex)} · {labelFor(ACTIVITIES, form.activity_level)} · {labelFor(GOALS, form.goal)}
            </p>
          )}
          {editing && <button type="submit" disabled={busy || !ready}>{busy ? "Saving…" : "Save profile"}</button>}
        </form>

        <form
          className="card stack"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            setNotice("");
            try {
              const allergies = [...prefs.allergies];
              const custom = prefs.customAllergy.trim();
              if (custom && !allergies.includes(custom.toLowerCase())) allergies.push(custom);
              const saved = await api<Profile>("/api/profile/", {
                method: "PATCH",
                body: JSON.stringify({
                  allergies_status: prefs.allergies_status,
                  allergies: prefs.allergies_status === "listed" ? allergies : [],
                  dislikes: prefs.dislikes.split(",").map((item) => item.trim()).filter(Boolean),
                  diet_pattern: prefs.diet_pattern,
                  preferred_cuisines: prefs.preferred_cuisines,
                  preferred_language: prefs.preferred_language,
                }),
              });
              setPrefs((current) => ({
                ...current,
                allergies_status: saved.allergies_status ?? "",
                allergies: saved.allergies ?? [],
                customAllergy: "",
                dislikes: (saved.dislikes ?? []).join(", "),
                diet_pattern: saved.diet_pattern ?? "",
                preferred_cuisines: saved.preferred_cuisines ?? [],
                preferred_language: saved.preferred_language || "en",
              }));
              setNotice("Food preferences saved.");
            } catch (err) {
              setError(messageFrom(err));
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Food Preferences & Allergies</h2>
          <p className="muted">Allergy information is not assumed. Choose not yet provided, no allergies declared, or list specific allergies. Name-based filters cannot guarantee the absence of an allergen in prepared food.</p>
          <label>
            Allergy information
            <select value={prefs.allergies_status} onChange={(event) => setPrefs({ ...prefs, allergies_status: event.target.value })}>
              <option value="">Not yet provided</option>
              <option value="none">No allergies declared</option>
              <option value="listed">Allergies listed</option>
            </select>
          </label>
          {prefs.allergies_status === "listed" ? (
            <fieldset>
              <legend>Allergies</legend>
              <div className="chip-row">
                {ALLERGY_CHOICES.map((name) => (
                  <label key={name} className="chip">
                    <input
                      type="checkbox"
                      checked={prefs.allergies.includes(name)}
                      onChange={(event) =>
                        setPrefs((current) => ({
                          ...current,
                          allergies: event.target.checked ? [...current.allergies, name] : current.allergies.filter((item) => item !== name),
                        }))
                      }
                    />
                    {name}
                  </label>
                ))}
              </div>
              <label>Custom allergy or ingredient<input value={prefs.customAllergy} onChange={(event) => setPrefs({ ...prefs, customAllergy: event.target.value })} /></label>
            </fieldset>
          ) : null}
          <label>Foods to avoid<input value={prefs.dislikes} onChange={(event) => setPrefs({ ...prefs, dislikes: event.target.value })} placeholder="Comma-separated names" /></label>
          <label>
            Dietary preference
            <select value={prefs.diet_pattern} onChange={(event) => setPrefs({ ...prefs, diet_pattern: event.target.value })}>
              <option value="">Not set</option>
              <option value="vegetarian">Vegetarian</option>
              <option value="vegan">Vegan</option>
              <option value="non_vegetarian">Non-vegetarian</option>
            </select>
          </label>
          <fieldset>
            <legend>Preferred cuisines</legend>
            <div className="chip-row">
              {CUISINE_CHOICES.map((name) => (
                <label key={name} className="chip">
                  <input
                    type="checkbox"
                    checked={prefs.preferred_cuisines.includes(name)}
                    onChange={(event) =>
                      setPrefs((current) => ({
                        ...current,
                        preferred_cuisines: event.target.checked
                          ? [...current.preferred_cuisines, name]
                          : current.preferred_cuisines.filter((item) => item !== name),
                      }))
                    }
                  />
                  {name}
                </label>
              ))}
            </div>
          </fieldset>
          <label>
            Preferred chat language
            <select value={prefs.preferred_language} onChange={(event) => setPrefs({ ...prefs, preferred_language: event.target.value })}>
              {SUPPORTED_LANGUAGES.map(([code, label]) => (
                <option key={code} value={code}>{label}</option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save preferences"}</button>
        </form>

        <section className="stack">
          <div className="page-head">
            <div>
              <h2>Your nutrition targets</h2>
              <p className="muted">These are your active numbers. A suggestion stays unsaved until you accept it.</p>
            </div>
            <button type="button" className="soft" onClick={suggest}>Calculate suggestion</button>
          </div>
          {current === undefined ? <p className="muted">Loading targets…</p> : null}
          {current === null ? <p className="banner">No active target yet.</p> : null}
          {current && (
            <div className="target-grid">
              {TARGET_FIELDS.map(([key, label, unit]) => (
                <article className="card" key={key}>
                  <p className="eyebrow">{label}</p>
                  <strong>{amount(current[key])}</strong>
                  <p className="muted">{unit} · {sourceLabel(current.source)}</p>
                </article>
              ))}
            </div>
          )}
          {suggestion && (
            <article className="card stack">
              <p className="eyebrow">Suggestion, not saved</p>
              <div className="nutrient-pills">
                {TARGET_FIELDS.map(([key, label, unit]) => (
                  <span key={key} data-nutrient={key}>{label} {amount(suggestion[key])} {unit}</span>
                ))}
              </div>
              {current?.source === "user_customized" && (
                <label>
                  <input type="checkbox" checked={replaceCustom} onChange={(event) => setReplaceCustom(event.target.checked)} />
                  {" "}Replace my custom target. The previous target stays in history.
                </label>
              )}
              <button type="button" onClick={accept}>Use this suggestion</button>
            </article>
          )}
          <form className="card stack" onSubmit={saveCustom}>
            <p className="eyebrow">Use your own numbers</p>
            <div className="field-grid">
              {TARGET_FIELDS.map(([key, label, unit]) => (
                <label key={key}>
                  {label} ({unit})
                  <input inputMode="decimal" value={custom[key]} required onChange={(event) => setCustom({ ...custom, [key]: event.target.value })} />
                </label>
              ))}
            </div>
            <button type="submit" className="soft">Save my numbers</button>
          </form>
          <article className="card">
            <p className="eyebrow">Earlier targets</p>
            {history.filter((row) => row.effective_until).length === 0 ? <p className="muted">No earlier targets.</p> : null}
            <ul className="plain">
              {history.filter((row) => row.effective_until).map((row) => (
                <li key={row.id}>{sourceLabel(row.source)} · {amount(row.calories)} kcal · closed {row.effective_until}</li>
              ))}
            </ul>
          </article>
        </section>
      </div>
    </div>
  );
}

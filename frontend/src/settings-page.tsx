import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { applyAppearance } from "./appearance";
import { SUPPORTED_LANGUAGES } from "./languages";
import type { Profile } from "./pages";
import { MonitorIcon, MoonIcon, SunIcon } from "./icons";
import { useSession } from "./session";

const APPEARANCE_MODES = [
  ["light", "Light", SunIcon],
  ["dark", "Dark", MoonIcon],
  ["system", "System", MonitorIcon],
] as const;

type Target = {
  source: string;
  calories: string;
  protein_g: string;
  carbohydrates_g: string;
  fat_g: string;
  fibre_g: string;
  weekly_calories: string | null;
  weekly_protein_g: string | null;
  weekly_carbohydrates_g: string | null;
  weekly_fat_g: string | null;
  weekly_fibre_g: string | null;
};

type UserFood = {
  id: number;
  name: string;
  ingredients: string;
  serving_amount: string;
  serving_unit: string;
  energy_kcal: string | null;
  protein_g: string | null;
  carb_g: string | null;
  fat_g: string | null;
  fibre_g: string | null;
  allergen_status: string;
};

const TABS = ["account", "goals", "diet", "foods", "voice"] as const;
const ALLERGY_CHOICES = ["milk", "egg", "peanut", "tree nut", "wheat", "soy", "fish", "shellfish", "sesame", "mustard"];
const RESTRICTIONS = ["vegetarian", "vegan", "jain", "no onion", "no garlic"];
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

export function SettingsPage() {
  const { user, logout } = useSession();
  const [params, setParams] = useSearchParams();
  const tab = TABS.includes(params.get("tab") as (typeof TABS)[number]) ? (params.get("tab") as (typeof TABS)[number]) : "account";
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [weekly, setWeekly] = useState<Record<string, string>>({});
  const [foods, setFoods] = useState<UserFood[]>([]);
  const [foodForm, setFoodForm] = useState({ name: "", ingredients: "", serving_amount: "1", serving_unit: "serving", energy_kcal: "", protein_g: "", carb_g: "", fat_g: "", fibre_g: "" });
  const [likes, setLikes] = useState("");
  const [notes, setNotes] = useState("");
  const [dislikes, setDislikes] = useState("");
  const [customRestriction, setCustomRestriction] = useState("");

  function load() {
    return Promise.all([
      api<Profile>("/api/profile/"),
      api<{ target: Target | null }>("/api/targets/"),
      api<{ results: UserFood[] }>("/api/user-foods/"),
    ]).then(([nextProfile, targets, userFoods]) => {
      setProfile(nextProfile);
      applyAppearance(nextProfile.appearance || "light");
      setTarget(targets.target);
      setCustom({
        calories: targets.target?.calories ?? "",
        protein_g: targets.target?.protein_g ?? "",
        carbohydrates_g: targets.target?.carbohydrates_g ?? "",
        fat_g: targets.target?.fat_g ?? "",
        fibre_g: targets.target?.fibre_g ?? "",
      });
      setWeekly({
        weekly_calories: targets.target?.weekly_calories ?? "",
        weekly_protein_g: targets.target?.weekly_protein_g ?? "",
        weekly_carbohydrates_g: targets.target?.weekly_carbohydrates_g ?? "",
        weekly_fat_g: targets.target?.weekly_fat_g ?? "",
        weekly_fibre_g: targets.target?.weekly_fibre_g ?? "",
      });
      setLikes((nextProfile.likes ?? []).join(", "));
      setNotes(nextProfile.notes ?? "");
      setDislikes((nextProfile.dislikes ?? []).join(", "));
      setFoods(userFoods.results);
    });
  }

  useEffect(() => {
    load().catch((err) => setError(messageFrom(err)));
  }, []);

  async function patchProfile(body: Record<string, unknown>, ok: string) {
    setError("");
    setNotice("");
    try {
      const saved = await api<Profile>("/api/profile/", { method: "PATCH", body: JSON.stringify(body) });
      setProfile(saved);
      if (body.appearance) applyAppearance(String(body.appearance));
      setNotice(ok);
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function saveGoals(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const payload: Record<string, string | null> = { ...custom };
      for (const [key, value] of Object.entries(weekly)) {
        payload[key] = value.trim() ? value : null;
      }
      await api("/api/targets/customize/", { method: "POST", body: JSON.stringify(payload) });
      setNotice("Goals saved. The previous target remains in history.");
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  async function saveFood(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api("/api/user-foods/", {
        method: "POST",
        body: JSON.stringify({
          ...foodForm,
          energy_kcal: foodForm.energy_kcal || null,
          protein_g: foodForm.protein_g || null,
          carb_g: foodForm.carb_g || null,
          fat_g: foodForm.fat_g || null,
          fibre_g: foodForm.fibre_g || null,
        }),
      });
      setNotice("Personal food saved as user-provided nutrition.");
      setFoodForm({ name: "", ingredients: "", serving_amount: "1", serving_unit: "serving", energy_kcal: "", protein_g: "", carb_g: "", fat_g: "", fibre_g: "" });
      await load();
    } catch (err) {
      setError(messageFrom(err));
    }
  }

  return (
    <div className="stack fit-page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Account and preferences</h1>
        </div>
      </header>
      <div className="segment-row" role="tablist">
        {TABS.map((name) => (
          <button key={name} type="button" className={tab === name ? "" : "ghost"} onClick={() => setParams({ tab: name })}>
            {name === "foods" ? "My Foods" : name[0].toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>
      {error ? <p className="banner error" role="alert">{error}</p> : null}
      {notice ? <p className="banner">{notice}</p> : null}

      {tab === "account" && profile ? (
        <div className="stack">
          <section className="card stack">
            <p><strong>{user?.name}</strong></p>
            <p className="muted">{user?.email}</p>
            <div className="row-actions">
              <button type="button" className="ghost" onClick={() => void logout()}>Sign out</button>
            </div>
          </section>
          <form
            className="card stack"
            onSubmit={(event) => {
              event.preventDefault();
              void patchProfile({ appearance: profile.appearance || "light" }, "Appearance saved.");
            }}
          >
            <fieldset className="appearance-choices">
              <legend>Appearance</legend>
              {APPEARANCE_MODES.map(([mode, label, Icon]) => (
                <label key={mode}>
                  <input
                    type="radio"
                    name="appearance"
                    checked={(profile.appearance || "light") === mode}
                    onChange={() => setProfile({ ...profile, appearance: mode })}
                  />
                  <Icon size={28} />
                  <span>{label}</span>
                </label>
              ))}
            </fieldset>
            <div className="row-actions">
              <button type="submit">Save appearance</button>
            </div>
          </form>
        </div>
      ) : null}

      {tab === "goals" ? (
        <form className="card stack" onSubmit={(event) => void saveGoals(event)}>
          <p className="muted">Daily numbers stay as you set them. Weekly numbers are optional; Progress uses daily × 7 when they are empty.</p>
          {TARGET_FIELDS.map(([key, label, unit]) => (
            <label key={key}>
              Daily {label} ({unit})
              <input value={custom[key] ?? ""} onChange={(event) => setCustom((current) => ({ ...current, [key]: event.target.value }))} />
            </label>
          ))}
          <label>
            Weekly calories (optional)
            <input value={weekly.weekly_calories ?? ""} onChange={(event) => setWeekly((current) => ({ ...current, weekly_calories: event.target.value }))} />
          </label>
          <button type="submit">Save goals</button>
          <p className="muted">Current source: {target?.source ?? "none"}.</p>
        </form>
      ) : null}

      {tab === "diet" && profile ? (
        <form
          className="card stack"
          onSubmit={(event) => {
            event.preventDefault();
            const restrictions = [...(profile.restrictions ?? [])];
            if (customRestriction.trim()) restrictions.push(`custom:${customRestriction.trim()}`);
            void patchProfile(
              {
                allergies_status: profile.allergies_status,
                allergies: profile.allergies,
                dislikes: dislikes.split(",").map((item) => item.trim()).filter(Boolean),
                diet_pattern: profile.diet_pattern,
                restrictions,
                likes: likes.split(",").map((item) => item.trim()).filter(Boolean),
                notes,
              },
              "Diet preferences saved.",
            );
          }}
        >
          <fieldset>
            <legend>Allergies</legend>
            <label><input type="radio" checked={profile.allergies_status === ""} onChange={() => setProfile({ ...profile, allergies_status: "" })} /> Not yet provided</label>
            <label><input type="radio" checked={profile.allergies_status === "none"} onChange={() => setProfile({ ...profile, allergies_status: "none", allergies: [] })} /> None declared</label>
            <label><input type="radio" checked={profile.allergies_status === "listed"} onChange={() => setProfile({ ...profile, allergies_status: "listed" })} /> Listed</label>
            {ALLERGY_CHOICES.map((name) => (
              <label key={name}>
                <input
                  type="checkbox"
                  checked={(profile.allergies ?? []).includes(name)}
                  onChange={(event) => {
                    const next = new Set(profile.allergies ?? []);
                    if (event.target.checked) next.add(name);
                    else next.delete(name);
                    setProfile({ ...profile, allergies_status: "listed", allergies: [...next] });
                  }}
                />
                {name}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Restrictions</legend>
            {RESTRICTIONS.map((name) => (
              <label key={name}>
                <input
                  type="checkbox"
                  checked={(profile.restrictions ?? []).includes(name)}
                  onChange={(event) => {
                    const next = new Set(profile.restrictions ?? []);
                    if (event.target.checked) next.add(name);
                    else next.delete(name);
                    setProfile({ ...profile, restrictions: [...next] });
                  }}
                />
                {name}
              </label>
            ))}
            <label>Custom restriction<input value={customRestriction} onChange={(event) => setCustomRestriction(event.target.value)} /></label>
          </fieldset>
          <label>Dislikes<input value={dislikes} onChange={(event) => setDislikes(event.target.value)} /></label>
          <label>Likes<input value={likes} onChange={(event) => setLikes(event.target.value)} /></label>
          <label>Notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          <button type="submit">Save diet</button>
        </form>
      ) : null}

      {tab === "foods" ? (
        <div className="stack">
          <form className="card stack" onSubmit={(event) => void saveFood(event)}>
            <p className="muted">User-provided nutrition. These foods are never written into the Anuvaad catalogue. Incomplete ingredients stay unverified.</p>
            <label>Name<input value={foodForm.name} onChange={(event) => setFoodForm({ ...foodForm, name: event.target.value })} required /></label>
            <label>Ingredients<textarea value={foodForm.ingredients} onChange={(event) => setFoodForm({ ...foodForm, ingredients: event.target.value })} /></label>
            <label>Serving amount<input value={foodForm.serving_amount} onChange={(event) => setFoodForm({ ...foodForm, serving_amount: event.target.value })} /></label>
            <label>Serving unit<input value={foodForm.serving_unit} onChange={(event) => setFoodForm({ ...foodForm, serving_unit: event.target.value })} /></label>
            <label>kcal<input value={foodForm.energy_kcal} onChange={(event) => setFoodForm({ ...foodForm, energy_kcal: event.target.value })} /></label>
            <button type="submit">Add food</button>
          </form>
          <ul className="plain">
            {foods.map((food) => (
              <li key={food.id} className="card">
                <strong>{food.name}</strong>
                <p className="muted">User-provided nutrition · {food.allergen_status === "unverified" ? "allergen status unverified" : "ingredients listed"}</p>
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    api(`/api/user-foods/${food.id}/`, { method: "DELETE" })
                      .then(() => load())
                      .catch((err) => setError(messageFrom(err)));
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {tab === "voice" && profile ? (
        <form
          className="card stack"
          onSubmit={(event) => {
            event.preventDefault();
            void patchProfile(
              { preferred_language: profile.preferred_language },
              "Voice settings saved.",
            );
          }}
        >
          <fieldset className="language-grid">
            <legend>Preferred language</legend>
            {SUPPORTED_LANGUAGES.map(([code, english, native]) => (
              <label key={code}>
                <input
                  type="radio"
                  name="preferred_language"
                  value={code}
                  checked={(profile.preferred_language || "en") === code}
                  onChange={() => setProfile({ ...profile, preferred_language: code })}
                />
                <span className="language-native" lang={code} dir="auto">{native}</span>
                <span className="language-english">{english}</span>
              </label>
            ))}
          </fieldset>
          <p className="muted">Replies stay on the page. Voice input is still available in Coach.</p>
          <button type="submit">Save voice</button>
        </form>
      ) : null}
    </div>
  );
}

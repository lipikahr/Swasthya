import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";
import { localIsoDay, shiftDay } from "./dates";
import { FoodPicker, type FoodSuggestion } from "./food-autocomplete";
import { ChevronLeftIcon, ChevronRightIcon, LeafIcon, MEAL_ICONS, PlusIcon, SwapIcon, TrashIcon } from "./icons";
import "./plan.css";

type Slot = {
  id: number;
  slot: string;
  label?: string;
  position?: number;
  source?: string;
  food_name: string;
  quantity: string;
  unit: string;
  status: string;
  provenance: string;
  nutrition_snapshot: Record<string, string | null>;
  food_code?: string;
  user_food_id?: number | null;
  reasons?: string[];
};

type Plan = {
  id?: number | null;
  date: string | null;
  slots: Slot[];
  limitation: string | null;
  totals?: Record<string, string | null>;
  target_calories?: string | null;
  preferences?: { diet: string; cuisines: string[]; goal: string; avoid_sweets: boolean };
};

type Alternative = {
  food_code: string;
  user_food_id: number | null;
  food_name: string;
  quantity: string;
  unit: string;
  provenance: string;
};

const SLOTS = ["breakfast", "lunch", "snack", "dinner"] as const;
type SlotName = (typeof SLOTS)[number];

type Draft = {
  meal: SlotName | "other";
  part: SlotName;
  label: string;
  quantity: string;
  unit: string;
  food?: FoodSuggestion;
};

const EMPTY_DRAFT: Draft = { meal: "breakfast", part: "snack", label: "", quantity: "1", unit: "serving" };

function mealTitle(slot: string) {
  return slot[0].toUpperCase() + slot.slice(1);
}

export function PlanPage() {
  const navigate = useNavigate();
  const [date, setDate] = useState(() => localIsoDay());
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [swapFor, setSwapFor] = useState<number | null>(null);
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);

  function load(onDate = date) {
    return api<Plan>(`/api/day-plans/?date=${onDate}`).then(setPlan);
  }

  useEffect(() => {
    load(date).catch((err) => setError(err instanceof ApiError ? err.message : "Plan could not be loaded."));
  }, [date]);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      setPlan(await api<Plan>("/api/day-plans/", { method: "POST", body: JSON.stringify({ date }) }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "A plan could not be generated.");
    } finally {
      setBusy(false);
    }
  }

  async function openSwap(slotId: number) {
    setError("");
    try {
      const body = await api<{ alternatives: Alternative[]; limitation: string | null }>(`/api/day-plans/slots/${slotId}/swap/`);
      setSwapFor(slotId);
      setAlternatives(body.alternatives);
      if (body.limitation) setError(body.limitation);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Swap options were not available.");
    }
  }

  async function acceptSwap(option: Alternative) {
    if (swapFor == null) return;
    setBusy(true);
    try {
      setPlan(
        await api<Plan>(`/api/day-plans/slots/${swapFor}/swap/`, {
          method: "POST",
          body: JSON.stringify({ food_code: option.food_code, user_food_id: option.user_food_id }),
        }),
      );
      setSwapFor(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That swap could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function logThis(slotId: number) {
    setBusy(true);
    try {
      const body = await api<{ conversation_id: number }>(`/api/day-plans/slots/${slotId}/log/`, { method: "POST", body: "{}" });
      navigate(`/coach?conversation=${body.conversation_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Coach could not open this planned food.");
      setBusy(false);
    }
  }

  async function addItem(event: FormEvent) {
    event.preventDefault();
    if (!draft.food) {
      setError("Choose a food from the verified list first.");
      return;
    }
    const extra = draft.meal === "other";
    const name = draft.label.trim();
    if (extra && !name) {
      setError("Name the extra meal, for example Pre-workout.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setPlan(
        await api<Plan>("/api/day-plans/slots/", {
          method: "POST",
          body: JSON.stringify({
            date,
            slot: extra ? draft.part : draft.meal,
            label: extra ? name : "",
            food_code: draft.food.food_code,
            user_food_id: draft.food.user_food_id,
            quantity: draft.quantity || "1",
            unit: draft.unit || draft.food.serving_unit || "serving",
          }),
        }),
      );
      setDraft(EMPTY_DRAFT);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That food could not be added.");
    } finally {
      setBusy(false);
    }
  }

  async function removeItem(slotId: number) {
    setBusy(true);
    try {
      setPlan(await api<Plan>(`/api/day-plans/slots/${slotId}/`, { method: "DELETE" }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That item could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  const prefs = plan?.preferences;
  const chips = [
    prefs?.diet,
    ...(prefs?.cuisines ?? []),
    prefs?.goal,
    prefs?.avoid_sweets ? "Lower-sugar day" : "",
  ].filter(Boolean) as string[];

  return (
    <div className="fit-page plan-page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Plan</p>
          <h1>Today’s food plan</h1>
          <p className="muted">Planned foods are not eaten until you confirm them in Coach. Add your own items, or generate a day that follows your diet and cuisine.</p>
        </div>
      </header>
      <section className="card plan-controls">
        <div className="plan-controls-top">
          <div className="plan-date">
            <span className="plan-date-label">Date</span>
            <div className="plan-date-row">
              <button type="button" className="icon-nav ghost" aria-label="Previous day" onClick={() => setDate(shiftDay(date, -1))}><ChevronLeftIcon /></button>
              <input type="date" value={date} onChange={(event) => setDate(event.target.value)} aria-label="Plan date" />
              <button type="button" className="icon-nav ghost" aria-label="Next day" onClick={() => setDate(shiftDay(date, 1))}><ChevronRightIcon /></button>
            </div>
          </div>
          <p className="plan-calories muted">{plan?.target_calories ? `${displayKcal(plan.totals?.energy_kcal)} / ${displayKcal(plan.target_calories)} kcal planned` : "No calorie target yet."}</p>
          <button type="button" className="plan-generate" onClick={() => void generate()} disabled={busy}>Generate / regenerate</button>
        </div>
        {chips.length ? (
          <div className="plan-chips">
            {chips.map((chip) => <span key={chip} className="chip"><LeafIcon size={14} /> {chip}</span>)}
            <Link className="text-link" to="/settings?tab=diet">Edit preferences</Link>
          </div>
        ) : (
          <p className="muted">Set diet, cuisine, and likes in <Link to="/settings?tab=diet">Settings</Link> so generated plans can follow them.</p>
        )}
      </section>
      {error ? <p className="banner error" role="alert">{error}</p> : null}
      {plan?.limitation ? <p className="banner">{plan.limitation}</p> : null}
      <form className="card plan-composer" onSubmit={(event) => void addItem(event)}>
        <div>
          <h2>Add meal</h2>
          <p className="muted">Breakfast, lunch, snack, and dinner are already on the day. Use this when you eat another meal, or to put a food on one of those four.</p>
        </div>
        <div className="plan-composer-fields">
          <label>
            <span>Meal</span>
            <select value={draft.meal} onChange={(event) => setDraft((current) => ({ ...current, meal: event.target.value as Draft["meal"] }))}>
              {SLOTS.map((slot) => <option key={slot} value={slot}>{mealTitle(slot)}</option>)}
              <option value="other">Another meal</option>
            </select>
          </label>
          {draft.meal === "other" ? (
            <>
              <label>
                <span>Name</span>
                <input value={draft.label} placeholder="Pre-workout" onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))} />
              </label>
              <label>
                <span>Part of the day</span>
                <select value={draft.part} onChange={(event) => setDraft((current) => ({ ...current, part: event.target.value as SlotName }))}>
                  {SLOTS.map((slot) => <option key={slot} value={slot}>{mealTitle(slot)}</option>)}
                </select>
              </label>
            </>
          ) : null}
          <div className="plan-field">
            <span>Food</span>
            <FoodPicker
              key={draft.food?.food_code ?? draft.food?.user_food_id ?? "none"}
              label="Food"
              placeholder="Search verified foods"
              disabled={busy}
              onSelect={(food) => setDraft((current) => ({ ...current, food, unit: food.serving_unit || current.unit }))}
            />
            {draft.food ? <p className="plan-chosen">{draft.food.food_name}</p> : null}
          </div>
          <label>
            <span>Quantity</span>
            <input value={draft.quantity} inputMode="decimal" onChange={(event) => setDraft((current) => ({ ...current, quantity: event.target.value }))} />
          </label>
          <label>
            <span>Unit</span>
            <input value={draft.unit} onChange={(event) => setDraft((current) => ({ ...current, unit: event.target.value }))} />
          </label>
          <button type="submit" disabled={busy}><PlusIcon /> Add meal</button>
        </div>
      </form>
      <div className="fit-grid plan-grid">
        {SLOTS.map((slot) => {
          const Icon = MEAL_ICONS[slot];
          const items = (plan?.slots ?? []).filter((item) => item.slot === slot && !item.label);
          return (
            <MealCard
              key={slot}
              title={mealTitle(slot)}
              icon={<Icon />}
              items={items}
              busy={busy}
              swapFor={swapFor}
              alternatives={alternatives}
              onSwap={openSwap}
              onAccept={acceptSwap}
              onLog={logThis}
              onRemove={removeItem}
            />
          );
        })}
        {extraMeals(plan?.slots ?? []).map((group) => (
          <MealCard
            key={group.key}
            title={group.label}
            note={mealTitle(group.slot)}
            items={group.items}
            busy={busy}
            swapFor={swapFor}
            alternatives={alternatives}
            onSwap={openSwap}
            onAccept={acceptSwap}
            onLog={logThis}
            onRemove={removeItem}
          />
        ))}
      </div>
      {!plan?.slots.length ? <p className="muted">Generate a plan for this date, add foods by hand, or <Link to="/coach">log a meal</Link> you already ate.</p> : null}
    </div>
  );
}

function extraMeals(slots: Slot[]) {
  const groups = new Map<string, { key: string; label: string; slot: string; items: Slot[] }>();
  for (const item of slots) {
    const label = item.label?.trim();
    if (!label) continue;
    const key = `${item.slot}:${label}`;
    const group = groups.get(key) ?? { key, label, slot: item.slot, items: [] };
    group.items.push(item);
    groups.set(key, group);
  }
  return [...groups.values()];
}

function MealCard({
  title,
  note,
  icon,
  items,
  busy,
  swapFor,
  alternatives,
  onSwap,
  onAccept,
  onLog,
  onRemove,
}: {
  title: string;
  note?: string;
  icon?: ReactNode;
  items: Slot[];
  busy: boolean;
  swapFor: number | null;
  alternatives: Alternative[];
  onSwap: (slotId: number) => void;
  onAccept: (option: Alternative) => void;
  onLog: (slotId: number) => void;
  onRemove: (slotId: number) => void;
}) {
  return (
    <section className="card plan-slot fit-panel">
      <h2>{icon} {title}</h2>
      {note ? <p className="muted plan-note">Logged with {note.toLowerCase()}</p> : null}
      <div className="fit-scroll stack">
        {items.length ? items.map((item) => (
          <article key={item.id} className="plan-item">
            <strong>{item.food_name}</strong>
            <p className="muted">
              {item.quantity} {item.unit} · {displayKcal(item.nutrition_snapshot.energy_kcal)} kcal
              {item.provenance === "user_provided" ? " · User-provided nutrition" : " · Verified catalogue"}
            </p>
            {item.reasons?.length ? <p className="muted">{item.reasons.join(" · ")}</p> : null}
            <div className="plan-item-actions">
              <button type="button" className="ghost" onClick={() => void onSwap(item.id)} disabled={busy || item.status === "logged"}><SwapIcon /> Swap</button>
              <button type="button" onClick={() => void onLog(item.id)} disabled={busy || item.status === "logged"}>Log this</button>
              <button type="button" className="danger" onClick={() => void onRemove(item.id)} disabled={busy || item.status === "logged"}><TrashIcon /> Remove</button>
            </div>
            {swapFor === item.id
              ? alternatives.map((option) => (
                  <button key={`${option.food_code}-${option.user_food_id}`} type="button" className="ghost" onClick={() => void onAccept(option)}>
                    {option.food_name} · {option.quantity} {option.unit}
                  </button>
                ))
              : null}
          </article>
        )) : <p className="muted">Nothing planned yet.</p>}
      </div>
    </section>
  );
}

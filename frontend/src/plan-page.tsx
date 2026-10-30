import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "./api";
import { displayKcal } from "./chat-ui";

type Slot = {
  id: number;
  slot: string;
  food_name: string;
  quantity: string;
  unit: string;
  status: string;
  provenance: string;
  nutrition_snapshot: Record<string, string | null>;
  food_code?: string;
  user_food_id?: number | null;
};

type Plan = { date: string | null; slots: Slot[]; limitation: string | null };

type Alternative = {
  food_code: string;
  user_food_id: number | null;
  food_name: string;
  quantity: string;
  unit: string;
  provenance: string;
};

export function PlanPage() {
  const navigate = useNavigate();
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [swapFor, setSwapFor] = useState<number | null>(null);
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);

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

  return (
    <div className="stack">
      <header className="page-head">
        <div>
          <p className="eyebrow">Plan</p>
          <h1>Today’s food plan</h1>
          <p className="muted">Planned foods are not eaten until you confirm them in Coach.</p>
        </div>
        <button type="button" onClick={() => void generate()} disabled={busy}>Generate / regenerate</button>
      </header>
      <label>
        Date
        <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
      </label>
      {error ? <p className="banner error" role="alert">{error}</p> : null}
      {plan?.limitation ? <p className="banner">{plan.limitation}</p> : null}
      {(plan?.slots ?? []).map((slot) => (
        <article key={slot.id} className="card stack">
          <p className="eyebrow">{slot.slot} · {slot.status}</p>
          <h2>{slot.food_name}</h2>
          <p className="muted">
            {slot.quantity} {slot.unit} · {displayKcal(slot.nutrition_snapshot.energy_kcal)} kcal
            {slot.provenance === "user_provided" ? " · User-provided nutrition" : " · Verified catalogue"}
          </p>
          <div className="row-actions">
            <button type="button" className="ghost" onClick={() => void openSwap(slot.id)} disabled={busy || slot.status === "logged"}>
              Swap
            </button>
            <button type="button" onClick={() => void logThis(slot.id)} disabled={busy || slot.status === "logged"}>
              Log this
            </button>
          </div>
          {swapFor === slot.id
            ? alternatives.map((option) => (
                <button key={`${option.food_code}-${option.user_food_id}`} type="button" className="ghost" onClick={() => void acceptSwap(option)}>
                  {option.food_name} · {option.quantity} {option.unit}
                </button>
              ))
            : null}
        </article>
      ))}
      {!plan?.slots.length ? <p className="muted">Generate a plan for this date, or <Link to="/coach">log a meal</Link> you already ate.</p> : null}
    </div>
  );
}

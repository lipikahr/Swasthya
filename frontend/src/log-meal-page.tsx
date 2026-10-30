import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "./api";
import { CHAT_COPY, displayAssistantMessage } from "./chat-copy";
import {
  GREETINGS,
  PROGRESS_PATH,
  applyFoodSuggestion,
  autocompleteQuery,
  displayKcal,
  formatDisplayedKcal,
  recordingSupported,
  shouldStickToBottom,
  speechErrorText,
  speechStatus,
  visibleHistory,
} from "./chat-ui";

type Nutrients = Record<string, string | null>;

type ConfirmationItem = {
  food_code: string;
  user_food_id?: number | null;
  food_name: string;
  original_name?: string;
  quantity: string;
  unit: string;
  provenance?: string;
  nutrition: Nutrients;
};

type Confirmation = {
  meal_type: "breakfast" | "lunch" | "dinner" | "snack" | null;
  meal_type_required: boolean;
  items: ConfirmationItem[];
};

type MealSuggestion = {
  food_code: string;
  food_name: string;
  quantity: string;
  unit: string;
  reasons: string[];
};

type Celebration = {
  show: boolean;
  title: string;
  message: string;
};

type ChatReply = {
  status: string;
  conversation_id: number;
  message: string;
  meal_id: number | null;
  confirmation?: Confirmation | null;
  suggestions?: MealSuggestion[];
  allergy_note?: string;
  celebration?: Celebration | null;
  original_text?: string;
};

const MEAL_CATEGORIES = [
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "snack", label: "Snack" },
  { value: "dinner", label: "Dinner" },
] as const;

const EXAMPLE_PROMPTS = [
  "Log breakfast",
  "What is remaining today?",
  "Suggest lunch",
  "Generate a plan",
  "Weekly progress",
  "What did I eat yesterday?",
] as const;

const PREVIEW_KEYS = [
  ["energy_kcal", "Calories", "kcal"],
  ["protein_g", "Protein", "g"],
  ["carb_g", "Carbs", "g"],
  ["fat_g", "Fat", "g"],
  ["fibre_g", "Fibre", "g"],
] as const;

function messageFrom(err: unknown) {
  if (!(err instanceof ApiError)) return CHAT_COPY.genericError;
  const first = Object.values(err.details)[0];
  const detail = Array.isArray(first) ? first[0] : first;
  if (detail && String(detail) !== err.message) {
    return `${err.message} ${detail}`.trim();
  }
  return err.message;
}

function amount(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function nutrientAmount(key: string, value: string | null | undefined) {
  return key === "energy_kcal" ? displayKcal(value) : amount(value);
}

function MicIcon({ recording }: { recording: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      {recording ? (
        <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" />
      ) : (
        <>
          <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" fill="currentColor" />
          <path d="M6 11a6 6 0 0 0 12 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M12 17v3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

function pickRecorderMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return types.find((type) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) ?? "";
}

export function LogMealPage() {
  const [params] = useSearchParams();
  const [text, setText] = useState("");
  const [side, setSide] = useState<{ remaining: string | null; goal_label: string } | null>(null);
  const [listenError, setListenError] = useState("");
  const [autoplay, setAutoplay] = useState(false);
  const [preferredLanguage, setPreferredLanguage] = useState("en");
  const composerRef = useRef<HTMLInputElement>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [turns, setTurns] = useState<Array<{ role: string; content: string }>>([]);
  const [chatReady, setChatReady] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [editingMeal, setEditingMeal] = useState(false);
  const [editItems, setEditItems] = useState<Array<{ food_name: string; quantity: string; unit: string }>>([]);
  const [greeting] = useState(() => GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
  const [listening, setListening] = useState(false);
  const [speechError, setSpeechError] = useState("");
  const [showLatest, setShowLatest] = useState(false);
  const [suggestions, setSuggestions] = useState<Array<{ food_code: string; food_name: string }>>([]);
  const [mealSuggestions, setMealSuggestions] = useState<MealSuggestion[]>([]);
  const [allergyNote, setAllergyNote] = useState("");
  const [celebration, setCelebration] = useState<Celebration | null>(null);
  const [activeSuggestion, setActiveSuggestion] = useState(0);
  const voiceSupported = recordingSupported();
  const sendingRef = useRef(false);
  const confirmingRef = useRef(false);
  const logRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const transcribeSeq = useRef(0);
  const recordLimitRef = useRef<number | null>(null);
  const MAX_RECORD_MS = 28000;
  const wantListenRef = useRef(false);
  const suggestSeq = useRef(0);

  function scrollToLatest() {
    stickRef.current = true;
    setShowLatest(false);
    endRef.current?.scrollIntoView({ block: "end" });
  }

  useLayoutEffect(() => {
    if (!stickRef.current) return;
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns, confirmation, chatError, chatBusy, editingMeal, listening, greeting]);

  useEffect(() => {
    return () => {
      wantListenRef.current = false;
      recorderRef.current?.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    const query = autocompleteQuery(text);
    if (!query || listening) {
      setSuggestions([]);
      return;
    }
    const seq = ++suggestSeq.current;
    const timer = window.setTimeout(() => {
      api<{ results: Array<{ food_code: string; food_name: string }> }>(
        `/api/foods/search/?q=${encodeURIComponent(query)}&suggest=1&limit=5`,
      )
        .then((body) => {
          if (seq !== suggestSeq.current) return;
          setSuggestions(body.results.slice(0, 5));
          setActiveSuggestion(0);
        })
        .catch(() => {
          if (seq === suggestSeq.current) setSuggestions([]);
        });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [text, listening]);

  useEffect(() => {
    if (params.get("compose") === "1") composerRef.current?.focus();
  }, [params]);

  useEffect(() => {
    api<{ progress: { remaining: Record<string, string | null> | null; goal_label: string } }>("/api/dashboard/")
      .then((body) => setSide({ remaining: body.progress.remaining?.calories ?? null, goal_label: body.progress.goal_label }))
      .catch(() => setSide(null));
    api<{ autoplay_replies?: boolean; preferred_language?: string }>("/api/profile/")
      .then((profile) => {
        setAutoplay(Boolean(profile.autoplay_replies));
        setPreferredLanguage(profile.preferred_language || "en");
      })
      .catch(() => setAutoplay(false));
  }, []);

  useEffect(() => {
    let cancelled = false;
    const requested = params.get("conversation");
    const start = requested
      ? api<{ id: number; messages: Array<{ role: string; content: string }> }>(`/api/conversations/${requested}/`).then((detail) => ({ results: [{ id: detail.id }], detail }))
      : api<{ results: Array<{ id: number }> }>("/api/conversations/").then((list) => ({ results: list.results, detail: null }));
    start
      .then(async (list) => {
        const latest = list.results[0];
        if (!latest || cancelled) return;
        const detailReply =
          list.detail ?? (await api<{ id: number; messages: Array<{ role: string; content: string }> }>(`/api/conversations/${latest.id}/`));
        if (cancelled || sendingRef.current) return;
        setConversationId(detailReply.id);
        setTurns(visibleHistory(detailReply.messages.map((message) => ({ role: message.role, content: message.content }))));
        const pending = await api<ChatReply>(`/api/agent/draft/?conversation_id=${detailReply.id}`);
        if (!cancelled && !sendingRef.current) setConfirmation(pending.confirmation ?? null);
      })
      .catch((err) => {
        if (!cancelled) setChatError(messageFrom(err));
      })
      .finally(() => {
        if (!cancelled) setChatReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [params]);

  function onLogScroll() {
    const node = logRef.current;
    if (!node) return;
    const near = shouldStickToBottom(node.scrollTop, node.scrollHeight, node.clientHeight);
    stickRef.current = near;
    setShowLatest((current) => (current === !near ? current : !near));
  }

  function stopTracks() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  async function transcribeBlob(blob: Blob, seq: number) {
    const body = new FormData();
    body.append("audio", blob, "speech.webm");
    if (preferredLanguage) body.append("language", preferredLanguage);
    try {
      const result = await api<{ transcript: string; submitted: boolean }>("/api/agent/transcribe/", { method: "POST", body });
      if (seq !== transcribeSeq.current) return;
      if (result.submitted) return;
      setText(result.transcript);
    } catch (err) {
      if (seq !== transcribeSeq.current) return;
      setSpeechError(messageFrom(err));
    }
  }

  function stopListening() {
    wantListenRef.current = false;
    if (recordLimitRef.current != null) {
      window.clearTimeout(recordLimitRef.current);
      recordLimitRef.current = null;
    }
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    else {
      setListening(false);
      stopTracks();
    }
  }

  async function startListening() {
    if (!recordingSupported()) {
      setSpeechError(speechStatus(false, false, ""));
      return;
    }
    setSpeechError("");
    setSuggestions([]);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream, pickRecorderMime() ? { mimeType: pickRecorderMime() } : undefined);
      const seq = ++transcribeSeq.current;
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        setListening(false);
        recorderRef.current = null;
        stopTracks();
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        chunksRef.current = [];
        if (!blob.size) {
          setSpeechError(speechErrorText("no-speech"));
          return;
        }
        void transcribeBlob(blob, seq);
      };
      recorderRef.current = recorder;
      wantListenRef.current = true;
      setListening(true);
      recorder.start();
      recordLimitRef.current = window.setTimeout(() => {
        setSpeechError("Recording stopped at 28 seconds. Sarvam accepts about 30 seconds of audio.");
        stopListening();
      }, MAX_RECORD_MS);
    } catch (err) {
      const denied = err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "SecurityError");
      setSpeechError(denied ? speechErrorText("not-allowed") : "Microphone recording could not start. Type the meal instead.");
      setListening(false);
      stopTracks();
    }
  }

  function chooseSuggestion(foodName: string) {
    setText(applyFoodSuggestion(text, foodName));
    setSuggestions([]);
  }

  function onComposerKey(event: KeyboardEvent<HTMLInputElement>) {
    if (!suggestions.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestion((current) => (current + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestion((current) => (current - 1 + suggestions.length) % suggestions.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      chooseSuggestion(suggestions[activeSuggestion]?.food_name ?? "");
    } else if (event.key === "Escape") {
      setSuggestions([]);
    }
  }

  function appendAssistant(content: string) {
    const shown = formatDisplayedKcal(content);
    setTurns((current) => {
      const last = current[current.length - 1];
      if (last?.role === "assistant" && last.content === shown) return current;
      return [...current, { role: "assistant", content: shown }];
    });
  }

  async function listenTo(content: string) {
    setListenError("");
    try {
      const headers = new Headers();
      const access = sessionStorage.getItem("swasthya.access");
      if (access) headers.set("Authorization", `Bearer ${access}`);
      headers.set("Content-Type", "application/json");
      const response = await fetch("/api/agent/speak/", {
        method: "POST",
        headers,
        body: JSON.stringify({ text: content, language: preferredLanguage }),
      });
      if (!response.ok) {
        setListenError(
          response.status === 422
            ? "Spoken playback is not available for this language. The written reply is still available."
            : "Listen unavailable. The written reply is still available.",
        );
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      await audio.play();
    } catch {
      setListenError("Listen unavailable.");
    }
  }

  async function onImage(file: File | undefined) {
    if (!file) return;
    const body = new FormData();
    body.append("image", file);
    try {
      const result = await api<{ candidates: string[] }>("/api/agent/image/", { method: "POST", body });
      const names = result.candidates.filter(Boolean);
      if (!names.length) {
        setChatError("No food names were identified. Type the food instead.");
        return;
      }
      setText(names[0]);
      setChatError(`Candidate foods: ${names.join(", ")}. Confirm the identity, quantity, and meal before logging.`);
    } catch (err) {
      setChatError(messageFrom(err));
    }
  }

  async function selectCategory(value: "breakfast" | "lunch" | "dinner" | "snack") {
    if (!conversationId || confirmingRef.current) return;
    setConfirmation((current) => (current ? { ...current, meal_type: value, meal_type_required: false } : current));
    setChatError("");
    stickRef.current = true;
    try {
      const reply = await api<ChatReply>("/api/agent/draft/", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, action: "edit", meal_type: value }),
      });
      if (reply.confirmation) setConfirmation(reply.confirmation);
    } catch (err) {
      setChatError(messageFrom(err));
    }
  }

  async function applyEdit(event: FormEvent) {
    event.preventDefault();
    if (!conversationId || confirmingRef.current) return;
    setChatError("");
    stickRef.current = true;
    try {
      const reply = await api<ChatReply>("/api/agent/draft/", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: conversationId,
          action: "edit",
          items: editItems.map((item) => ({ food_query: item.food_name, quantity: item.quantity, unit: item.unit })),
        }),
      });
      setEditingMeal(false);
      setConfirmation(reply.confirmation ?? null);
      if (reply.message) appendAssistant(reply.message);
    } catch (err) {
      setChatError(messageFrom(err));
    }
  }

  async function cancelPending() {
    if (!conversationId || confirmingRef.current) return;
    setChatError("");
    stickRef.current = true;
    try {
      const reply = await api<ChatReply>("/api/agent/draft/", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, action: "cancel" }),
      });
      setConfirmation(null);
      setEditingMeal(false);
      if (reply.message) appendAssistant(reply.message);
    } catch (err) {
      setChatError(messageFrom(err));
    }
  }

  async function confirmMeal(event: FormEvent) {
    event.preventDefault();
    if (!conversationId || !confirmation?.meal_type || confirmingRef.current) return;
    confirmingRef.current = true;
    setConfirming(true);
    setChatError("");
    stickRef.current = true;
    try {
      const reply = await api<ChatReply>("/api/agent/confirm/", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, meal_type: confirmation.meal_type }),
      });
      if (reply.status === "SUCCESS" && reply.meal_id) {
        setConfirmation(null);
        setEditingMeal(false);
        appendAssistant(displayAssistantMessage(reply.status, reply.message));
        if (reply.celebration?.show) setCelebration(reply.celebration);
      } else {
        const content = reply.message || CHAT_COPY.genericError;
        setChatError(content);
        appendAssistant(content);
      }
    } catch (err) {
      setChatError(messageFrom(err));
    } finally {
      confirmingRef.current = false;
      setConfirming(false);
    }
  }

  async function sendChat(event: FormEvent) {
    event.preventDefault();
    const message = text.trim();
    if (!message || !chatReady || sendingRef.current) return;
    stopListening();
    sendingRef.current = true;
    stickRef.current = true;
    setText("");
    setSuggestions([]);
    setChatBusy(true);
    setChatError("");
    setSpeechError("");
    setTurns((current) => {
      const last = current[current.length - 1];
      if (last?.role === "user" && last.content === message) return current;
      return [...current, { role: "user", content: message }];
    });
    try {
      const reply = await api<ChatReply>("/api/agent/chat/", {
        method: "POST",
        body: JSON.stringify({ message, conversation_id: conversationId }),
      });
      setConversationId(reply.conversation_id);
      setConfirmation(reply.confirmation ?? null);
      setMealSuggestions(reply.suggestions ?? []);
      setAllergyNote(reply.allergy_note ?? "");
      setEditingMeal(false);
      const spoken = displayAssistantMessage(reply.status, reply.message);
      appendAssistant(spoken);
      if (autoplay) void listenTo(spoken);
    } catch (err) {
      const content = messageFrom(err);
      setChatError(content);
      appendAssistant(content);
    } finally {
      sendingRef.current = false;
      setChatBusy(false);
    }
  }

  const voiceNote = speechStatus(listening, voiceSupported, speechError);

  return (
    <div className="coach-layout">
    <div className="log-chat-page">
      <header className="chat-heading">
        <div>
          <p className="eyebrow">Coach</p>
          <h1>What did you eat?</h1>
          <p className="muted">Describe the food and how much. Nothing is saved until you confirm it.</p>
        </div>
        <Link className="button" to={PROGRESS_PATH}>View Progress</Link>
      </header>
      <section className="card stack chat-panel">
        {chatError ? <p className="banner error" role="alert">{chatError}</p> : null}
        <div className="chat-log" ref={logRef} onScroll={onLogScroll} aria-live="polite">
          {!chatReady ? <p className="muted">{CHAT_COPY.loading}</p> : null}
          <article className="bubble assistant greeting" data-greeting="true">
            <p>{greeting}</p>
          </article>
          {turns.map((turn, index) => (
            <article key={`${turn.role}-${index}`} className={`bubble ${turn.role === "user" ? "user" : "assistant"}`}>
              <p>{formatDisplayedKcal(turn.content)}</p>
              {turn.role === "assistant" ? (
                <button type="button" className="ghost" onClick={() => void listenTo(turn.content)}>Listen</button>
              ) : null}
            </article>
          ))}
          {confirmation ? (
            <form className="meal-confirm" onSubmit={editingMeal ? applyEdit : confirmMeal}>
              <p className="meal-confirm-title">Check this meal before I log it.</p>
              <ul className="plain">
                {editingMeal
                  ? editItems.map((item, index) => (
                      <li key={`${item.food_name}-${index}`}>
                        <div className="meal-edit-grid">
                          <label>
                            Food
                            <input
                              aria-label={`Food ${index + 1}`}
                              value={item.food_name}
                              onChange={(event) =>
                                setEditItems((current) => current.map((entry, entryIndex) => (entryIndex === index ? { ...entry, food_name: event.target.value } : entry)))
                              }
                            />
                          </label>
                          <label>
                            Quantity
                            <input
                              aria-label={`Quantity ${index + 1}`}
                              value={item.quantity}
                              onChange={(event) =>
                                setEditItems((current) => current.map((entry, entryIndex) => (entryIndex === index ? { ...entry, quantity: event.target.value } : entry)))
                              }
                            />
                          </label>
                          <label>
                            Unit
                            <input
                              aria-label={`Unit ${index + 1}`}
                              value={item.unit}
                              onChange={(event) =>
                                setEditItems((current) => current.map((entry, entryIndex) => (entryIndex === index ? { ...entry, unit: event.target.value } : entry)))
                              }
                            />
                          </label>
                        </div>
                      </li>
                    ))
                  : confirmation.items.map((item) => (
                      <li key={`${item.food_code}-${item.user_food_id ?? ""}-${item.food_name}`}>
                        <strong>{item.food_name}</strong>
                        {item.original_name && item.original_name !== item.food_name ? <p className="muted">{item.original_name}</p> : null}
                        <p className="muted">{amount(item.quantity)} {item.unit}{item.provenance === "user_provided" ? " · User-provided nutrition" : ""}</p>
                        <div className="nutrient-pills">
                          {PREVIEW_KEYS.map(([key, label, nutrientUnit]) => (
                            <span key={key}>{label} {nutrientAmount(key, item.nutrition[key])} {nutrientUnit}</span>
                          ))}
                        </div>
                      </li>
                    ))}
              </ul>
              <fieldset className="meal-category">
                <legend>Which meal should I log this as?</legend>
                <div className="meal-segment" role="radiogroup" aria-label="Which meal should I log this as?">
                  {MEAL_CATEGORIES.map((option) => (
                    <label key={option.value}>
                      <input
                        type="radio"
                        name="confirm-meal-type"
                        value={option.value}
                        checked={confirmation.meal_type === option.value}
                        onChange={() => selectCategory(option.value)}
                        disabled={confirming}
                      />
                      {option.label}
                    </label>
                  ))}
                </div>
              </fieldset>
              {!confirmation.meal_type ? <p className="muted">Select breakfast, lunch, snack, or dinner before logging this meal.</p> : null}
              <div className="row-actions">
                {editingMeal ? (
                  <>
                    <button type="submit" disabled={confirming}>Save edit</button>
                    <button type="button" className="ghost" onClick={() => setEditingMeal(false)} disabled={confirming}>Back</button>
                  </>
                ) : (
                  <>
                    <button type="submit" disabled={!confirmation.meal_type || confirming}>Confirm & Log</button>
                    <button
                      type="button"
                      className="ghost"
                      disabled={confirming}
                      onClick={() => {
                        setEditItems(confirmation.items.map((item) => ({ food_name: item.food_name, quantity: item.quantity, unit: item.unit })));
                        setEditingMeal(true);
                      }}
                    >
                      Edit
                    </button>
                    <button type="button" className="ghost" onClick={cancelPending} disabled={confirming}>Cancel</button>
                  </>
                )}
              </div>
            </form>
          ) : null}
          {mealSuggestions.length ? (
            <article className="card stack meal-ideas">
              <p className="eyebrow">Suggestions, not logged meals</p>
              {allergyNote ? <p className="muted">{allergyNote}</p> : null}
              {mealSuggestions.map((item) => (
                <button
                  key={item.food_code}
                  type="button"
                  className="ghost idea-button"
                  onClick={() => {
                    setText(`I ate ${item.quantity} ${item.unit} ${item.food_name}`);
                    setMealSuggestions([]);
                  }}
                >
                  {item.food_name} · {item.quantity} {item.unit}
                  <span className="muted">{item.reasons.join(" · ")}</span>
                </button>
              ))}
            </article>
          ) : null}
          {chatBusy ? <p className="muted">{CHAT_COPY.busy}</p> : null}
          <div ref={endRef} />
        </div>
        {showLatest ? (
          <button type="button" className="soft latest-button" onClick={scrollToLatest}>Latest message</button>
        ) : null}
        {voiceNote ? <p className="muted voice-status" role="status">{voiceNote}</p> : null}
        {listenError ? <p className="muted" role="status">{listenError}</p> : null}
        <div className="composer-wrap">
          {suggestions.length ? (
            <ul className="food-suggest" role="listbox" aria-label="Food suggestions">
              {suggestions.map((food, index) => (
                <li key={food.food_code}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === activeSuggestion}
                    className={index === activeSuggestion ? "is-active" : ""}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => chooseSuggestion(food.food_name)}
                  >
                    {food.food_name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <form className="composer" onSubmit={sendChat}>
            <label className="visually-hidden">Describe what you ate</label>
            <input
              ref={composerRef}
              value={text}
              aria-label="Describe what you ate"
              aria-autocomplete="list"
              placeholder={CHAT_COPY.placeholder}
              onChange={(event) => setText(event.target.value)}
              onKeyDown={onComposerKey}
              disabled={chatBusy || !chatReady}
            />
            <button
              type="button"
              className={`mic-button ${listening ? "is-recording" : "ghost"}`}
              aria-pressed={listening}
              aria-label={listening ? "Stop voice input" : "Start voice input"}
              title={listening ? "Stop voice input" : "Start voice input"}
              disabled={chatBusy || !chatReady}
              onClick={listening ? stopListening : startListening}
            >
              <MicIcon recording={listening} />
            </button>
            <label className="ghost image-upload">
              Photo
              <input className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void onImage(event.target.files?.[0])} />
            </label>
            <button type="submit" disabled={chatBusy || !chatReady}>Send</button>
          </form>
        </div>
      </section>
      {celebration ? (
        <div className="celebrate" role="status">
          <div className="celebrate-card">
            <p className="eyebrow">Daily goal reached!</p>
            <h2>{celebration.title}</h2>
            <p>{celebration.message}</p>
            <button type="button" onClick={() => setCelebration(null)}>Continue</button>
          </div>
        </div>
      ) : null}
    </div>
    <aside className="card stack coach-side">
      <p className="eyebrow">Today</p>
      <p>{side ? `${side.goal_label}. ${side.remaining == null ? "Remaining unknown" : `${side.remaining} kcal remaining`}.` : "Loading today’s progress…"}</p>
      <Link to="/diary">Open diary</Link>
      <p className="eyebrow">Try asking</p>
      {EXAMPLE_PROMPTS.map((prompt) => (
        <button key={prompt} type="button" className="ghost" onClick={() => setText(prompt)}>{prompt}</button>
      ))}
    </aside>
    </div>
  );
}

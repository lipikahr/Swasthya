export const PROGRESS_PATH = "/progress";

export const GREETINGS = [
  "Welcome back. What did you eat today?",
  "Ready to log your next meal?",
  "What would you like to record today?",
] as const;

export function keepSingleGreeting(existing: string | null, incoming: string) {
  return existing ?? incoming;
}

export function displayKcal(value: string | null | undefined) {
  if (value == null || value === "") return "unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "unknown";
  return String(Math.round(number));
}

export function formatDisplayedKcal(text: string) {
  return text.replace(/(\d+\.\d+)(\s*kcal)/gi, (_match, value: string, suffix: string) => `${Math.round(Number(value))}${suffix}`);
}

export function shouldStickToBottom(scrollTop: number, scrollHeight: number, clientHeight: number, threshold = 80) {
  return scrollHeight - scrollTop - clientHeight <= threshold;
}

export function speechErrorText(code: string) {
  if (code === "not-allowed" || code === "service-not-allowed") {
    return "Microphone permission was denied. You can type the meal instead.";
  }
  if (code === "no-speech") return "No speech was detected. Try again.";
  if (code === "aborted") return "";
  return "Voice input could not be understood. Try again.";
}

export function speechStatus(listening: boolean, supported: boolean, error: string) {
  if (!supported) return "This browser cannot record audio. Type your meal instead.";
  if (listening) return "Listening. Stop when you are done, then edit the text before sending. Recordings are sent to Sarvam for transcription and are not stored by Swasthya.";
  return error;
}

export function recordingSupported() {
  return typeof window !== "undefined" && typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);
}

const AUTOCOMPLETE_SKIP = new Set([
  "i",
  "we",
  "ate",
  "had",
  "eaten",
  "have",
  "for",
  "and",
  "a",
  "an",
  "the",
  "of",
  "one",
  "two",
  "some",
  "hi",
  "hello",
  "hey",
  "thanks",
  "thank",
  "you",
  "good",
  "morning",
  "please",
]);

export function autocompleteQuery(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (/^(hi+|hello|hey+|thanks|thank you|good (morning|afternoon|evening))$/i.test(trimmed)) return null;
  const last = (trimmed.split(/\s+/).pop() || "").replace(/[^\p{L}\p{M}\p{N}]+/gu, "");
  if (last.length < 2 || AUTOCOMPLETE_SKIP.has(last.toLowerCase()) || /^\d/.test(last)) return null;
  return last;
}

export function applyFoodSuggestion(composer: string, foodName: string) {
  const trimmed = composer.replace(/\s+$/, "");
  if (!trimmed) return foodName;
  const parts = trimmed.split(/\s+/);
  const last = parts[parts.length - 1] || "";
  if (last && !/^\d/.test(last) && /[A-Za-z]/.test(last)) {
    parts[parts.length - 1] = foodName;
    return parts.join(" ");
  }
  return `${trimmed} ${foodName}`;
}

export function shouldRestartRecognition(intentActive: boolean, error: string) {
  if (!intentActive) return false;
  return !["not-allowed", "service-not-allowed", "audio-capture"].includes(error);
}

export function composeTranscript(existing: string, heard: string) {
  const base = existing.trim();
  const next = heard.trim();
  if (!next) return base;
  if (!base) return next;
  return `${base} ${next}`;
}

export function shouldSubmitAfterSpeech() {
  return false;
}

export function isCatalogueDump(content: string) {
  return content.startsWith("Which food did you mean?") && content.split(",").length > 3;
}

export function visibleHistory(messages: Array<{ role: string; content: string }>) {
  return messages.filter((message) => !isCatalogueDump(message.content));
}

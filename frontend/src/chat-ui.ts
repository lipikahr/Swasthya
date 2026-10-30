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

function wholeKcal(value: string) {
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number)) : value;
}

export function formatDisplayedKcal(text: string) {
  return text
    .replace(/(\d+\.\d+)(\s*kcal)/gi, (_match, value: string, suffix: string) => `${wholeKcal(value)}${suffix}`)
    .replace(/(Calories eaten |Remaining )(\d+\.\d+)/gi, (_match, label: string, value: string) => `${label}${wholeKcal(value)}`)
    .replace(/\d+\.\d{4,}/g, (value) => wholeKcal(value));
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export type StructuredReply = {
  title?: string;
  rows?: Array<{ label: string; value: string }>;
  lines: string[];
};

function prettyDay(iso: string) {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) return iso;
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

function sentences(text: string) {
  return text
    .split(/(?<=\.)\s+(?=[A-Z0-9“"])/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/** Turn a stored reply into labeled rows or separate lines. Short replies stay as one line. */
export function structureAssistantReply(text: string): StructuredReply {
  const flat = formatDisplayedKcal(text).replace(/\s+/g, " ").trim();
  const progress = flat.match(/^Saved meals on (\d{4}-\d{2}-\d{2}): (\d+)\. Calories eaten ([^.]+)\. Remaining ([^.]+)\. (.*)$/i);
  if (progress) {
    return {
      title: "Saved meals",
      rows: [
        { label: "Date", value: prettyDay(progress[1]) },
        { label: "Meals", value: progress[2] },
        { label: "Calories eaten", value: progress[3].trim() },
        { label: "Remaining", value: progress[4].trim() },
      ],
      lines: [progress[5].replace(/\.$/, "").trim()],
    };
  }
  const logged = flat.match(/^Logged (.+?)\.(?: About (.+) kcal remains for today\.)?$/i);
  if (logged) {
    const rows = [{ label: "Meal", value: logged[1].trim() }];
    if (logged[2]) rows.push({ label: "Remaining", value: `${logged[2].trim()} kcal` });
    return { title: "Logged", rows, lines: [] };
  }
  const units = flat.match(/^(.*) can be logged in (.+?)\. (.+) (?:is not a verified unit for this food|has no verified serving basis)\.?$/i);
  if (units) {
    return {
      title: units[1].trim(),
      rows: [
        { label: "Use", value: units[2].trim() },
        { label: "Not used", value: units[3].trim() },
      ],
      lines: [],
    };
  }
  const choices = flat.match(/^Which food did you mean\? (.+?)\.?$/i);
  if (choices) {
    return { title: "Which food did you mean?", rows: [], lines: choices[1].split(",").map((name) => name.trim()).filter(Boolean) };
  }
  const amount = flat.match(/^How much (.+?) did you eat\?\s*(.*)$/i);
  if (amount && amount[2]) {
    return { title: `How much ${amount[1].trim()} did you eat?`, rows: [], lines: sentences(amount[2]) };
  }
  const lines = sentences(flat);
  return { lines: lines.length > 1 ? lines : [flat] };
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

const MAX_PHRASE_WORDS = 3;

/**
 * The food words at the end of what the user is typing, for example "masala do" in "I ate two masala do".
 * Works for any script. Returns null when the text ends with a space, a number, or a filler word.
 */
export function trailingFoodPhrase(text: string): { phrase: string; start: number } | null {
  if (!text || /\s$/.test(text)) return null;
  const trimmed = text.trim();
  if (!trimmed) return null;
  if (/^(hi+|hello|hey+|thanks|thank you|good (morning|afternoon|evening))$/i.test(trimmed)) return null;
  const offset = text.indexOf(trimmed);
  const tokens = [...trimmed.matchAll(/[\p{L}\p{M}\p{N}]+/gu)];
  const last = tokens[tokens.length - 1];
  if (!last || last.index + last[0].length !== trimmed.length) return null;
  if (last[0].length < 2 || AUTOCOMPLETE_SKIP.has(last[0].toLowerCase()) || /^\d/.test(last[0])) return null;
  let first = tokens.length - 1;
  while (first > 0 && tokens.length - first < MAX_PHRASE_WORDS) {
    const previous = tokens[first - 1];
    const gap = trimmed.slice(previous.index + previous[0].length, tokens[first].index);
    if (!/^\s+$/.test(gap)) break;
    if (AUTOCOMPLETE_SKIP.has(previous[0].toLowerCase()) || /^\d/.test(previous[0])) break;
    first -= 1;
  }
  const start = tokens[first].index;
  return { phrase: trimmed.slice(start), start: offset + start };
}

export function autocompleteQuery(text: string) {
  const found = trailingFoodPhrase(text);
  if (!found) return null;
  return found.phrase;
}

export function applyFoodSuggestion(composer: string, foodName: string, matchedQuery?: string) {
  const trimmed = composer.replace(/\s+$/, "");
  if (!trimmed) return foodName;
  if (matchedQuery && trimmed.endsWith(matchedQuery)) return `${trimmed.slice(0, trimmed.length - matchedQuery.length)}${foodName}`;
  const found = trailingFoodPhrase(composer);
  if (found) return `${composer.slice(0, found.start)}${foodName}`;
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

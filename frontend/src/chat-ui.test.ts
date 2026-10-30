import assert from "node:assert/strict";
import test from "node:test";
import { SUPPORTED_LANGUAGE_CODES } from "./languages.ts";
import {
  GREETINGS,
  PROGRESS_PATH,
  applyFoodSuggestion,
  autocompleteQuery,
  composeTranscript,
  displayKcal,
  formatDisplayedKcal,
  structureAssistantReply,
  keepSingleGreeting,
  shouldRestartRecognition,
  shouldStickToBottom,
  isCatalogueDump,
  shouldSubmitAfterSpeech,
  speechErrorText,
  speechStatus,
  visibleHistory,
} from "./chat-ui.ts";

test("calories round only for display", () => {
  assert.equal(displayKcal("68.9"), "69");
  assert.equal(displayKcal("124.4"), "124");
  assert.equal(displayKcal("562.7"), "563");
  assert.equal(displayKcal(null), "unknown");
  assert.equal(formatDisplayedKcal("Logged about 68.9 kcal."), "Logged about 69 kcal.");
  assert.equal(formatDisplayedKcal("Protein 1.2 g"), "Protein 1.2 g");
  assert.equal(
    formatDisplayedKcal("Calories eaten 993.699981689453160000. Remaining 1006.300018310546840000."),
    "Calories eaten 994. Remaining 1006.",
  );
});

test("progress and unit replies are structured", () => {
  const progress = structureAssistantReply(
    "Saved meals on 2026-10-30: 2. Calories eaten 993.699981689453160000. Remaining 1006.300018310546840000. Below target.",
  );
  assert.equal(progress.title, "Saved meals");
  assert.deepEqual(
    progress.rows?.map((row) => row.value),
    ["30 October 2026", "2", "994", "1006"],
  );
  assert.deepEqual(progress.lines, ["Below target"]);
  const units = structureAssistantReply(
    "Rasam can be logged in grams, kilograms, or curry bowl. bowl is not a verified unit for this food.",
  );
  assert.equal(units.title, "Rasam");
  assert.equal(units.rows?.[0].value, "grams, kilograms, or curry bowl");
  assert.equal(units.rows?.[1].value, "bowl");
  assert.deepEqual(structureAssistantReply("Okay, I won't log that meal.").lines, ["Okay, I won't log that meal."]);
});

test("a visit keeps one greeting and the dashboard route stays protected", () => {
  const first = keepSingleGreeting(null, GREETINGS[0]);
  assert.equal(keepSingleGreeting(first, GREETINGS[1]), first);
  assert.equal(PROGRESS_PATH, "/progress");
});

test("scrolling follows the latest message only when the reader is already there", () => {
  assert.equal(shouldStickToBottom(900, 1000, 80), true);
  assert.equal(shouldStickToBottom(100, 1000, 80), false);
});

test("opening the log page keeps one local greeting and hides catalogue dumps", () => {
  const greeting = keepSingleGreeting(null, GREETINGS[0]);
  assert.equal(keepSingleGreeting(greeting, GREETINGS[2]), greeting);
  const history = visibleHistory([
    { role: "user", content: "I ate 1 chapati" },
    { role: "assistant", content: "Which food did you mean? Afghani chicken, Almond cake, Banana chips, Besan chilla." },
    { role: "assistant", content: "How much Chapati/Roti did you eat?" },
  ]);
  assert.equal(history.length, 2);
  assert.equal(isCatalogueDump(history[1].content), false);
});

test("recording intent survives a pause and only the user can stop it", () => {
  assert.equal(shouldRestartRecognition(true, ""), true);
  assert.equal(shouldRestartRecognition(true, "no-speech"), true);
  assert.equal(shouldRestartRecognition(true, "aborted"), true);
  assert.equal(shouldRestartRecognition(false, ""), false);
  assert.equal(shouldRestartRecognition(true, "not-allowed"), false);
  assert.equal(shouldSubmitAfterSpeech(), false);
});

test("typing a food prefix keeps quantity and never submits", () => {
  assert.equal(autocompleteQuery("chap"), "chap");
  assert.equal(autocompleteQuery("I ate 2 chap"), "chap");
  assert.equal(autocompleteQuery("hi"), null);
  assert.equal(autocompleteQuery("I ate 2"), null);
  assert.equal(autocompleteQuery("ಇಡ್ಲಿ"), "ಇಡ್ಲಿ");
  assert.equal(applyFoodSuggestion("I ate 2 chap", "Chapati/Roti"), "I ate 2 Chapati/Roti");
  assert.equal(applyFoodSuggestion("", "Idli"), "Idli");
});

test("autocomplete reads a short phrase, any script, and stops after a space", () => {
  assert.equal(autocompleteQuery("I ate two masala do"), "masala do");
  assert.equal(autocompleteQuery("I ate 2 chapati and sam"), "sam");
  assert.equal(autocompleteQuery("chapati "), null);
  assert.equal(autocompleteQuery("ನಾನು ಎರಡು ಇಡ್ಲಿ"), "ನಾನು ಎರಡು ಇಡ್ಲಿ");
  assert.equal(applyFoodSuggestion("I ate two masala do", "Masala dosa"), "I ate two Masala dosa");
  assert.equal(applyFoodSuggestion("मैंने इड", "Idli", "इड"), "मैंने Idli");
});

test("speech stays in the composer and is not auto-submitted", () => {
  assert.equal(composeTranscript("", "ನಾನು ಚಪಾತಿ ತಿಂದೆ"), "ನಾನು ಚಪಾತಿ ತಿಂದೆ");
  assert.equal(shouldSubmitAfterSpeech(), false);
  assert.match(speechErrorText("not-allowed"), /permission was denied/i);
  assert.match(speechErrorText("no-speech"), /No speech/);
  assert.match(speechStatus(false, false, ""), /cannot record audio/i);
  assert.match(speechStatus(true, true, ""), /Listening/);
  assert.match(speechStatus(true, true, ""), /Sarvam/);
  assert.equal(SUPPORTED_LANGUAGE_CODES.length, 23);
});

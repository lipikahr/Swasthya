export const CHAT_COPY = {
  title: "Nutrition Assistant",
  intro: "Describe what you ate and how much. A meal is saved only after you confirm it.",
  placeholder: "e.g., 2 idlis and a bowl of sambar",
  empty: "Try describing a meal, such as “2 idlis and a bowl of sambar”.",
  busy: "Preparing your response…",
  loading: "Loading conversation…",
  genericError: "We couldn't process your request. Please try again.",
};

export function displayAssistantMessage(status: string | undefined, message: string) {
  const text = (message || "").trim();
  if (status === "ERROR" && (!text || /traceback \(most recent call last\)/i.test(text))) {
    return CHAT_COPY.genericError;
  }
  return text || message;
}

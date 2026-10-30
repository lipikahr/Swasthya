export type Appearance = "light" | "dark" | "system";

export const APPEARANCE_STORAGE_KEY = "swasthya.appearance";

export function readStoredAppearance(): Appearance {
  try {
    const value = localStorage.getItem(APPEARANCE_STORAGE_KEY);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch {
    /* private mode */
  }
  return "light";
}

export function applyAppearance(mode: string | null | undefined) {
  const value: Appearance = mode === "dark" || mode === "light" || mode === "system" ? mode : "light";
  document.documentElement.dataset.theme = value;
  try {
    localStorage.setItem(APPEARANCE_STORAGE_KEY, value);
  } catch {
    /* private mode */
  }
}

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { api } from "./api";
import { trailingFoodPhrase } from "./chat-ui";

export type FoodSuggestion = {
  food_code: string;
  food_name: string;
  provenance?: string;
  user_food_id?: number | null;
  serving_unit?: string;
  matched_alias?: string | null;
};

type SearchBody = { results: FoodSuggestion[] };

/** Looks up foods for the words being typed. Tries the last few words, then just the last word. */
export function useFoodSuggestions(text: string, enabled = true) {
  const [items, setItems] = useState<FoodSuggestion[]>([]);
  const [query, setQuery] = useState("");
  const [suppressed, setSuppressed] = useState<string | null>(null);

  useEffect(() => {
    const found = enabled && text !== suppressed ? trailingFoodPhrase(text) : null;
    if (!found) {
      setItems([]);
      setQuery("");
      return;
    }
    const controller = new AbortController();
    const words = found.phrase.split(/\s+/);
    const queries = words.length > 1 ? [found.phrase, words[words.length - 1]] : [found.phrase];
    const timer = window.setTimeout(async () => {
      for (const q of queries) {
        try {
          const body = await api<SearchBody>(`/api/foods/search/?q=${encodeURIComponent(q)}&suggest=1&limit=6`, { signal: controller.signal });
          if (controller.signal.aborted) return;
          if (body.results.length) {
            setItems(body.results.slice(0, 6));
            setQuery(q);
            return;
          }
        } catch {
          if (controller.signal.aborted) return;
        }
      }
      if (!controller.signal.aborted) {
        setItems([]);
        setQuery("");
      }
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [text, enabled, suppressed]);

  return {
    items,
    query,
    /** Hide suggestions until the text changes again (used right after choosing one). */
    suppress: (value: string) => {
      setSuppressed(value);
      setItems([]);
    },
    dismiss: () => setItems([]),
  };
}

export function SuggestionList({
  id,
  items,
  active,
  onPick,
  onHover,
}: {
  id: string;
  items: FoodSuggestion[];
  active: number;
  onPick: (food: FoodSuggestion) => void;
  onHover?: (index: number) => void;
}) {
  if (!items.length) return null;
  return (
    <ul className="food-suggest" role="listbox" id={id} aria-label="Food suggestions">
      {items.map((food, index) => (
        <li key={`${food.food_code}-${food.user_food_id ?? ""}-${food.food_name}`} role="presentation">
          <button
            type="button"
            role="option"
            id={`${id}-${index}`}
            aria-selected={index === active}
            className={index === active ? "is-active" : ""}
            onMouseDown={(event) => event.preventDefault()}
            onMouseEnter={() => onHover?.(index)}
            onClick={() => onPick(food)}
          >
            <span className="food-suggest-name">{food.food_name}</span>
            {food.matched_alias && food.matched_alias.toLowerCase() !== food.food_name.toLowerCase() ? (
              <span className="food-suggest-alias">{food.matched_alias}</span>
            ) : null}
            <span className={`food-suggest-tag${food.provenance === "user_provided" ? " is-mine" : ""}`}>
              {food.provenance === "user_provided" ? "My food" : "Verified"}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Stand-alone food picker (used on the Plan page). Calls onSelect with the chosen food. */
export function FoodPicker({
  label,
  placeholder,
  onSelect,
  disabled,
}: {
  label: string;
  placeholder?: string;
  onSelect: (food: FoodSuggestion) => void;
  disabled?: boolean;
}) {
  const [text, setText] = useState("");
  const [active, setActive] = useState(0);
  const listId = useId();
  const { items, suppress, dismiss } = useFoodSuggestions(text, !disabled);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setActive(0);
  }, [items]);

  function pick(food: FoodSuggestion) {
    suppress(food.food_name);
    setText(food.food_name);
    onSelect(food);
    setText("");
    inputRef.current?.focus();
  }

  function onKey(event: KeyboardEvent<HTMLInputElement>) {
    if (!items.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((current) => (current + 1) % items.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => (current - 1 + items.length) % items.length);
    } else if (event.key === "Enter" || event.key === "Tab") {
      if (event.key === "Enter") event.preventDefault();
      pick(items[active] ?? items[0]);
    } else if (event.key === "Escape") {
      dismiss();
    }
  }

  return (
    <div className="food-picker">
      <label className="visually-hidden" htmlFor={`${listId}-input`}>{label}</label>
      <input
        id={`${listId}-input`}
        ref={inputRef}
        value={text}
        disabled={disabled}
        placeholder={placeholder ?? "Search a food"}
        role="combobox"
        aria-expanded={items.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={items.length ? `${listId}-${active}` : undefined}
        autoComplete="off"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKey}
      />
      <SuggestionList id={listId} items={items} active={active} onPick={pick} onHover={setActive} />
    </div>
  );
}

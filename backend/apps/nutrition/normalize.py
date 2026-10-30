"""Normalize food names for catalogue matching without rewriting user text."""

from __future__ import annotations

import re
import unicodedata

_ZERO_WIDTH = re.compile(r"[\u200b-\u200d\u2060\ufeff]")
_SPACE = re.compile(r"\s+")
_LATIN = re.compile(r"[A-Za-z]")

_DIGIT_PAIRS = {
    "٠١٢٣٤٥٦٧٨٩": "0123456789",
    "۰۱۲۳۴۵۶۷۸۹": "0123456789",
    "०१२३४५६७८९": "0123456789",
    "০১২৩৪৫৬৭৮৯": "0123456789",
    "૦૧૨૩૪૫૬૭૮૯": "0123456789",
    "୦୧୨୩୪୫୬୭୮୯": "0123456789",
    "௦௧௨௩௪௫௬௭௮௯": "0123456789",
    "౦౧౨౩౪౫౬౭౮౯": "0123456789",
    "೦೧೨೩೪೫೬೭೮೯": "0123456789",
    "൦൧൨൩൪൫൬൭൮൯": "0123456789",
}
_DIGIT_TABLE = str.maketrans("".join(_DIGIT_PAIRS), "".join(_DIGIT_PAIRS.values()))


def fold_digits(text: str) -> str:
    return str(text or "").translate(_DIGIT_TABLE)


def normalize_alias(text: str) -> str:
    """Unicode, whitespace, and punctuation folding. Indic letters stay intact."""
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = _ZERO_WIDTH.sub("", value)
    value = fold_digits(value)
    value = "".join(" " if unicodedata.category(ch)[0] in {"P", "S"} else ch for ch in value)
    value = _SPACE.sub(" ", value).strip()
    if _LATIN.search(value) and not re.search(r"[\u0900-\u0D7F\u0980-\u09FF]", value):
        return value.casefold()
    return value.casefold() if value.isascii() else value


def food_tokens(text: str) -> list[str]:
    normalized = normalize_alias(text)
    tokens = [token for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE) if len(token) >= 2]
    return tokens


def has_indic_letters(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u0D7F]", text or ""))

"""Curated multilingual aliases for verified Anuvaad foods.

Unverified or model-generated names must not be written here. Each alias is
attached only when the canonical catalogue row exists.
"""

from __future__ import annotations

from .models import Food, FoodAlias
from .normalize import normalize_alias

# (canonical food_name fragment or exact name, language, alias)
CURATED_ALIASES: tuple[tuple[str, str, str], ...] = (
    ("Idli", "en", "idli"),
    ("Idli", "en", "idly"),
    ("Idli", "en", "idlis"),
    ("Idli", "kn", "ಇಡ್ಲಿ"),
    ("Idli", "kn", "ಇಡ್ಲೀ"),
    ("Idli", "hi", "इडली"),
    ("Idli", "hi", "इडलि"),
    ("Idli", "ta", "இட்லி"),
    ("Idli", "te", "ఇడ్లీ"),
    ("Idli", "te", "ఇడ్లి"),
    ("Idli", "bn", "ইডলি"),
    ("Idli", "ml", "ഇഡ്ലി"),
    ("Idli", "mr", "इडली"),
    ("Semolina idli (Suji/Rava idli)", "en", "rava idli"),
    ("Semolina idli (Suji/Rava idli)", "en", "suji idli"),
    ("Semolina upma (Suji/Rava upma)", "en", "rava upma"),
    ("Semolina upma (Suji/Rava upma)", "en", "suji upma"),
    ("Semolina upma (Suji/Rava upma)", "en", "sooji upma"),
    ("Semolina upma", "en", "rava upma"),
    ("Semolina upma", "en", "suji upma"),
    ("Semolina upma", "kn", "ರವೆ ಉಪ್ಪಿಟ್ಟು"),
    ("Semolina upma (Suji/Rava upma)", "kn", "ರವೆ ಉಪ್ಪಿಟ್ಟು"),
    ("Semolina upma", "hi", "रवा उपमा"),
    ("Vegetable upma", "en", "veg upma"),
    ("Chapati/Roti", "en", "chapati"),
    ("Chapati/Roti", "en", "roti"),
    ("Chapati/Roti", "en", "chapathi"),
    ("Chapati/Roti", "kn", "ಚಪಾತಿ"),
    ("Chapati/Roti", "kn", "ರೋಟಿ"),
    ("Chapati/Roti", "hi", "चपाती"),
    ("Chapati/Roti", "hi", "रोटी"),
    ("Chapati/Roti", "ta", "சப்பாத்தி"),
    ("Chapati/Roti", "te", "చపాతి"),
    ("Sambar", "en", "sambar"),
    ("Sambar", "en", "sambhar"),
    ("Sambar", "kn", "ಸಾಂಬಾರ್"),
    ("Sambar", "hi", "सांबार"),
    ("Sambar", "ta", "சாம்பார்"),
    ("Sambar", "te", "సాంబార్"),
    ("Plain dosa", "en", "dosa"),
    ("Plain dosa", "en", "dose"),
    ("Plain dosa", "kn", "ದೋಸೆ"),
    ("Plain dosa", "hi", "डोसा"),
    ("Plain dosa", "ta", "தோசை"),
    ("Plain dosa", "te", "దోసె"),
    ("Masala dosa", "en", "masala dosa"),
    ("Masala dosa", "kn", "ಮಸಾಲ ದೋಸೆ"),
    ("Cow milk", "en", "cow milk"),
    ("Boiled rice (Uble chawal)", "en", "boiled rice"),
    ("Boiled rice (Uble chawal)", "en", "rice"),
    ("Boiled rice (Uble chawal)", "hi", "चावल"),
    ("Boiled rice (Uble chawal)", "kn", "ಅನ್ನ"),
    ("Poha", "en", "poha"),
    ("Poha", "hi", "पोहा"),
    ("Curd", "en", "curd"),
    ("Curd", "en", "dahi"),
    ("Curd", "hi", "दही"),
    ("Tea", "en", "tea"),
    ("Tea", "hi", "चाय"),
    ("Coffee", "en", "coffee"),
    ("Banana", "en", "banana"),
    ("Banana", "hi", "केला"),
    ("Apple", "en", "apple"),
    ("Egg", "en", "egg"),
    ("Egg", "en", "boiled egg"),
    ("Paneer", "en", "paneer"),
    ("Chicken", "en", "chicken"),
    ("Fish", "en", "fish"),
    ("Dal", "en", "dal"),
    ("Dal", "hi", "दाल"),
    ("Rasam", "en", "rasam"),
    ("Vada", "en", "vada"),
    ("Medu vada", "en", "medu vada"),
    ("Pongal", "en", "pongal"),
    ("Paratha", "en", "paratha"),
    ("Paratha", "hi", "पराठा"),
    ("Pulao", "en", "pulao"),
    ("Biryani", "en", "biryani"),
    ("Lassi", "en", "lassi"),
    ("Buttermilk", "en", "buttermilk"),
    ("Coconut chutney", "en", "coconut chutney"),
    ("Gulab jamun", "en", "gulab jamun"),
    ("Jalebi", "en", "jalebi"),
    ("Rasgulla", "en", "rasgulla"),
)


def canonical_food(name: str) -> Food | None:
    exact = list(Food.objects.filter(food_name__iexact=name).order_by("food_code")[:2])
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    partial = list(Food.objects.filter(food_name__iexact=name.split("(")[0].strip()).order_by("food_code")[:2])
    if len(partial) == 1:
        return partial[0]
    return None


def ensure_verified_aliases() -> int:
    created = 0
    for food_name, language, alias in CURATED_ALIASES:
        food = canonical_food(food_name)
        if food is None:
            continue
        normalized = normalize_alias(alias)
        if not normalized:
            continue
        _, was_created = FoodAlias.objects.get_or_create(
            food=food,
            language=language,
            normalized_alias=normalized,
            defaults={
                "alias_text": alias,
                "source": FoodAlias.Source.CURATED,
                "verified": True,
            },
        )
        if was_created:
            created += 1
    return created

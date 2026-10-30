"""Name-token classification for plan generation. Does not invent nutrient values."""

from __future__ import annotations

from .models import Food, FoodProfile

SWEET = ("laddu", "ladoo", "halwa", "halva", "payasam", "kheer", "barfi", "burfi", "jalebi", "gulab", "rasgulla", "rasmalai", "mysore pak", "jamun", "sweet", "mithai", "payesh", "shrikhand", "basundi")
FRIED = ("fried", "bhajji", "bajji", "pakora", "pakoda", "samosa", "vada", "bonda", "chips", "french fries", "puri", "poori", "kachori")
NONVEG = ("chicken", "mutton", "lamb", "goat", "beef", "pork", "fish", "prawn", "shrimp", "egg", "eggs", "omelette", "omelet", "keema", "biryani chicken")
EGG = ("egg", "eggs", "omelette", "omelet")
VEGAN_EXCLUDE = ("curd", "dahi", "ghee", "butter", "milk", "paneer", "cheese", "yogurt", "yoghurt", "cream", "honey")
BREAKFAST = ("idli", "dosa", "upma", "poha", "pongal", "paratha", "thepla", "uttapam", "oats", "cereal", "toast", "porridge")
SNACK = ("vada", "bonda", "samosa", "pakora", "chaat", "namkeen", "murukku", "mixture", "fries")
SOUTH = ("idli", "dosa", "sambar", "rasam", "upma", "pongal", "uttapam", "medu", "coconut", "avial", "appam", "puttu", "bisi bele")
NORTH = ("roti", "chapati", "paratha", "naan", "dal makhani", "paneer", "chole", "rajma", "poha", "litti", "kadhi")
WEST = ("thepla", "dhokla", "khandvi", "undhiyu", "pav bhaji", "misal", "poha")
EAST = ("luchi", "sandesh", "rasgulla", "macher", "shukto", "panta")
CUISINE = {
    "South Indian": SOUTH,
    "North Indian": NORTH,
    "Gujarati": ("thepla", "dhokla", "khandvi", "undhiyu", "fafda", "khaman"),
    "Bengali": ("luchi", "sandesh", "rasgulla", "macher", "shukto"),
    "Punjabi": ("paratha", "sarson", "makki", "chole", "paneer", "lassi", "naan"),
    "Maharashtrian": ("poha", "misal", "pav bhaji", "thalipeeth", "puran poli", "modak"),
}


def classify_name(name: str) -> dict:
    folded = (name or "").casefold()
    is_sweet = any(token in folded for token in SWEET)
    is_fried = any(token in folded for token in FRIED)
    if any(token in folded for token in NONVEG) and not any(token in folded for token in ("vegan", "veg ")):
        diet = "egg" if any(token in folded for token in EGG) and not any(token in folded for token in ("chicken", "mutton", "fish", "prawn", "shrimp", "beef", "pork")) else "nonveg"
    else:
        diet = "vegan" if not any(token in folded for token in VEGAN_EXCLUDE) else "veg"
    course = "any"
    if any(token in folded for token in BREAKFAST):
        course = "breakfast"
    elif any(token in folded for token in SNACK):
        course = "snack"
    region = "any"
    if any(token in folded for token in SOUTH):
        region = "south"
    elif any(token in folded for token in NORTH):
        region = "north"
    elif any(token in folded for token in WEST):
        region = "west"
    elif any(token in folded for token in EAST):
        region = "east"
    tags = [label for label, tokens in CUISINE.items() if any(token in folded for token in tokens)]
    return {
        "course": course,
        "region": region,
        "diet_class": diet,
        "is_sweet": is_sweet,
        "is_fried": is_fried,
        "cuisine_tags": tags,
    }


def profile_for(food: Food) -> dict:
    try:
        stored = food.profile
    except FoodProfile.DoesNotExist:
        stored = None
    if stored is not None:
        return {
            "course": stored.course,
            "region": stored.region,
            "diet_class": stored.diet_class,
            "is_sweet": stored.is_sweet,
            "is_fried": stored.is_fried,
            "cuisine_tags": stored.cuisine_tags or [],
        }
    return classify_name(food.food_name)


def upsert_profiles(limit: int = 0) -> int:
    count = 0
    foods = Food.objects.all().order_by("food_name")
    if limit:
        foods = foods[:limit]
    for food in foods:
        data = classify_name(food.food_name)
        FoodProfile.objects.update_or_create(food=food, defaults=data)
        count += 1
    return count

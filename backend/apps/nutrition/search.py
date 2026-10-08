from django.db.models import Q

from .calculation import active_version
from .embeddings import similar_foods
from .models import Food


def search_food(query: str, limit: int = 25, embed=None):
    version = active_version()
    text = query.strip()
    textual = list(
        Food.objects.filter(nutrition_rows__dataset_version=version)
        .filter(Q(food_name__icontains=text) | Q(food_code__iexact=text))
        .distinct()
        .order_by("food_name", "food_code")[:limit]
    )
    if len(textual) >= limit:
        return textual
    seen = {food.id for food in textual}
    for food in similar_foods(text, version, limit=limit, embed=embed):
        if food.id not in seen:
            textual.append(food)
            seen.add(food.id)
        if len(textual) >= limit:
            break
    return textual


def resolve_food(query: str, embed=None, semantic: bool = True) -> dict:
    """Pick one food only when the query matches a single verified record."""
    version = active_version()
    text = query.strip()
    foods = Food.objects.filter(nutrition_rows__dataset_version=version)
    exact_code = foods.filter(food_code__iexact=text).first()
    if exact_code is not None:
        return {"status": "resolved", "food": exact_code}

    exact_name = list(foods.filter(food_name__iexact=text).order_by("food_name")[:10])
    if len(exact_name) == 1:
        return {"status": "resolved", "food": exact_name[0]}
    if len(exact_name) > 1:
        return {"status": "ambiguous", "foods": exact_name}

    partial = list(foods.filter(food_name__icontains=text).order_by("food_name")[:10])
    if len(partial) == 1:
        return {"status": "resolved", "food": partial[0]}
    if len(partial) > 1:
        return {"status": "ambiguous", "foods": partial}
    if not semantic:
        return {"status": "not_found", "foods": []}

    neighbors = similar_foods(text, version, embed=embed)
    if neighbors:
        return {"status": "ambiguous", "foods": neighbors[:5]}
    return {"status": "not_found", "foods": []}

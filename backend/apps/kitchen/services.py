"""Recipe nutrition, weekly plans, and grocery aggregation.

Planned meals never create consumed meals. Nutrition is calculated through the
existing nutrition service. A recipe is complete only when every ingredient
resolves to a verified food and a supported quantity. Grams and kilograms may
be added together. Other units are combined only when the food and the unit
both match. Unmapped ingredients stay on their own lines.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.nutrition.calculation import NutritionError, WEIGHT_TO_GRAMS, calculate_nutrition
from apps.nutrition.nutrients import NUTRIENT_FIELDS
from apps.progress.services import get_daily_progress

from .catalogue import CATALOGUE, LICENSE_NOTE, SOURCE_NAME, SOURCE_NOTE
from .models import GroceryItem, GroceryList, MealPlan, PlannedMeal, Recipe, RecipeIngredient, SavedRecipe

SLOTS = [choice.value for choice in PlannedMeal.Slot]


def monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def quantity_str(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.001')):f}"


def nutrient_json(nutrients: dict | None) -> dict | None:
    if nutrients is None:
        return None
    return {name: None if nutrients[name] is None else str(nutrients[name]) for name in NUTRIENT_FIELDS}


def load_catalogue() -> dict:
    mapped = 0
    unmapped = 0
    for entry in CATALOGUE:
        recipe, _ = Recipe.objects.update_or_create(
            slug=entry["slug"],
            defaults={
                "title": entry["title"],
                "summary": entry["summary"],
                "instructions": entry["instructions"],
                "base_servings": Decimal(entry["base_servings"]),
                "source_name": SOURCE_NAME,
                "source_note": SOURCE_NOTE,
                "license_note": LICENSE_NOTE,
            },
        )
        recipe.ingredients.all().delete()
        for index, item in enumerate(entry["ingredients"]):
            food = None
            code = item.get("food_code")
            if code:
                from apps.nutrition.models import Food

                food = Food.objects.filter(food_code=code).first()
            if food is None:
                unmapped += 1
            else:
                mapped += 1
            RecipeIngredient.objects.create(
                recipe=recipe,
                food=food,
                label=item["label"],
                quantity=Decimal(item["quantity"]),
                unit=item["unit"],
                sort_order=index,
                note=item.get("note", ""),
            )
    return {"recipes": len(CATALOGUE), "mapped_ingredients": mapped, "unmapped_ingredients": unmapped}


def recipe_queryset(query: str):
    recipes = Recipe.objects.all()
    text = query.strip()
    if text:
        recipes = recipes.filter(
            Q(title__icontains=text) | Q(summary__icontains=text) | Q(ingredients__label__icontains=text)
        ).distinct()
    return recipes


def saved_id_set(user) -> set[int]:
    return set(SavedRecipe.objects.filter(user=user).values_list("recipe_id", flat=True))


def scale_factor(recipe: Recipe, servings: Decimal) -> Decimal:
    if servings <= 0:
        raise ValueError("Servings must be greater than zero.")
    return servings / recipe.base_servings


def recipe_nutrition(recipe: Recipe, servings: Decimal) -> dict:
    factor = scale_factor(recipe, servings)
    missing = []
    totals = {name: Decimal("0") for name in NUTRIENT_FIELDS}
    dataset_version = None
    calculation_version = None
    for ingredient in recipe.ingredients.all():
        amount = ingredient.quantity * factor
        if ingredient.food_id is None:
            missing.append(
                {
                    "label": ingredient.label,
                    "reason": ingredient.note or "No verified food is linked to this ingredient.",
                }
            )
            continue
        try:
            calculated = calculate_nutrition(ingredient.food.food_code, amount, ingredient.unit)
        except NutritionError as exc:
            missing.append({"label": ingredient.label, "reason": str(exc)})
            continue
        dataset_version = calculated["dataset_version"]
        calculation_version = calculated["calculation_version"]
        for name in NUTRIENT_FIELDS:
            value = calculated["nutrients"][name]
            if totals[name] is None or value is None:
                totals[name] = None
            else:
                totals[name] += value
    complete = not missing
    return {
        "status": "complete" if complete else "incomplete",
        "servings": quantity_str(servings),
        "dataset_version": dataset_version,
        "calculation_version": calculation_version,
        "nutrients": nutrient_json(totals) if complete else None,
        "missing": missing,
    }


def ingredient_json(ingredient: RecipeIngredient, factor: Decimal) -> dict:
    amount = ingredient.quantity * factor
    return {
        "id": ingredient.id,
        "label": ingredient.label,
        "quantity": quantity_str(amount),
        "unit": ingredient.unit,
        "food_code": None if ingredient.food_id is None else ingredient.food.food_code,
        "food_name": None if ingredient.food_id is None else ingredient.food.food_name,
        "mapped": ingredient.food_id is not None,
        "note": ingredient.note,
    }


def recipe_card(recipe: Recipe, saved_ids: set[int]) -> dict:
    nutrition = recipe_nutrition(recipe, recipe.base_servings)
    return {
        "slug": recipe.slug,
        "title": recipe.title,
        "summary": recipe.summary,
        "base_servings": quantity_str(recipe.base_servings),
        "source_name": recipe.source_name,
        "saved": recipe.id in saved_ids,
        "nutrition_status": nutrition["status"],
    }


def recipe_detail(recipe: Recipe, user, servings: Decimal) -> dict:
    factor = scale_factor(recipe, servings)
    return {
        "slug": recipe.slug,
        "title": recipe.title,
        "summary": recipe.summary,
        "instructions": recipe.instructions,
        "base_servings": quantity_str(recipe.base_servings),
        "servings": quantity_str(servings),
        "source_name": recipe.source_name,
        "source_note": recipe.source_note,
        "license_note": recipe.license_note,
        "saved": SavedRecipe.objects.filter(user=user, recipe=recipe).exists(),
        "ingredients": [ingredient_json(item, factor) for item in recipe.ingredients.select_related("food")],
        "nutrition": recipe_nutrition(recipe, servings),
    }


def week_plan(user, week_start: date) -> dict:
    plan = (
        MealPlan.objects.filter(user=user, week_start=week_start)
        .prefetch_related("entries__recipe__ingredients__food")
        .first()
    )
    entries = list(plan.entries.all()) if plan is not None else []
    days = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        day_entries = [entry for entry in entries if entry.date == day]
        slots = {slot: [] for slot in SLOTS}
        for entry in day_entries:
            slots[entry.slot].append(_entry_json(entry))
        days.append(
            {
                "date": day.isoformat(),
                "slots": slots,
                "nutrition": _day_plan_nutrition(day_entries),
            }
        )
    return {"week_start": week_start.isoformat(), "week_end": (week_start + timedelta(days=6)).isoformat(), "days": days}


def stored_servings(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def add_planned_meal(user, on_date: date, slot: str, recipe: Recipe, servings: Decimal) -> PlannedMeal:
    week_start = monday(on_date)
    plan, _ = MealPlan.objects.get_or_create(user=user, week_start=week_start)
    return PlannedMeal.objects.create(
        plan=plan,
        date=on_date,
        slot=slot,
        recipe=recipe,
        servings=stored_servings(servings),
    )


def _entry_json(entry: PlannedMeal) -> dict:
    nutrition = recipe_nutrition(entry.recipe, entry.servings)
    return {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "slot": entry.slot,
        "servings": quantity_str(entry.servings),
        "recipe": {
            "slug": entry.recipe.slug,
            "title": entry.recipe.title,
            "base_servings": quantity_str(entry.recipe.base_servings),
        },
        "nutrition": nutrition,
    }


def _day_plan_nutrition(entries: list[PlannedMeal]) -> dict:
    if not entries:
        return {"status": "empty", "nutrients": None, "note": "Nothing is planned for this day."}
    parts = [recipe_nutrition(entry.recipe, entry.servings) for entry in entries]
    if any(part["status"] != "complete" for part in parts):
        return {
            "status": "incomplete",
            "nutrients": None,
            "note": "Planned nutrition is incomplete because at least one recipe lacks a full verified calculation.",
        }
    totals = {name: Decimal("0") for name in NUTRIENT_FIELDS}
    for part in parts:
        for name in NUTRIENT_FIELDS:
            value = Decimal(part["nutrients"][name]) if part["nutrients"][name] is not None else None
            if totals[name] is None or value is None:
                totals[name] = None
            else:
                totals[name] += value
    return {
        "status": "complete",
        "nutrients": nutrient_json(totals),
        "note": "This is planned nutrition, not food that has been logged as eaten.",
    }


def grocery_for(user) -> GroceryList:
    grocery, _ = GroceryList.objects.get_or_create(user=user)
    return grocery


def grocery_payload(grocery: GroceryList, message: str | None = None) -> dict:
    items = grocery.items.select_related("food")
    rows = [_item_json(item) for item in items]
    return {
        "message": message,
        "outstanding_count": sum(1 for row in rows if not row["purchased"]),
        "items": rows,
    }


def _item_json(item: GroceryItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "quantity": quantity_str(item.quantity),
        "unit": item.unit,
        "purchased": item.purchased,
        "origin": item.origin,
        "food_code": None if item.food_id is None else item.food.food_code,
        "week_start": None if item.week_start is None else item.week_start.isoformat(),
    }


def generate_grocery(user, week_start: date) -> dict:
    grocery = grocery_for(user)
    grocery.items.filter(origin=GroceryItem.Origin.GENERATED, week_start=week_start).delete()
    plan = MealPlan.objects.filter(user=user, week_start=week_start).first()
    groups: dict[tuple, dict] = {}
    loose: list[dict] = []
    if plan is not None:
        entries = plan.entries.select_related("recipe").prefetch_related("recipe__ingredients__food")
        for entry in entries:
            factor = scale_factor(entry.recipe, entry.servings)
            for ingredient in entry.recipe.ingredients.all():
                amount = ingredient.quantity * factor
                _collect_ingredient(groups, loose, ingredient, amount, entry.recipe.title)
    GroceryItem.objects.bulk_create(
        [
            GroceryItem(
                grocery_list=grocery,
                name=row["name"],
                quantity=row["quantity"],
                unit=row["unit"],
                origin=GroceryItem.Origin.GENERATED,
                food=row["food"],
                week_start=week_start,
            )
            for row in list(groups.values()) + loose
        ]
    )
    message = (
        "Generated items for this week were replaced. Items you added yourself were kept. "
        "Quantities were combined only when the verified food and the unit matched, or when both amounts were weights in grams or kilograms."
    )
    if plan is None or not plan.entries.exists():
        message = (
            "No meals are planned for this week, so generated items for the week were cleared. "
            "Items you added yourself were kept."
        )
    return grocery_payload(grocery, message)


def _collect_ingredient(groups, loose, ingredient: RecipeIngredient, amount: Decimal, recipe_title: str):
    unit = ingredient.unit.strip().lower()
    if ingredient.food_id is not None and unit in WEIGHT_TO_GRAMS:
        grams = amount * WEIGHT_TO_GRAMS[unit]
        key = ("weight", ingredient.food_id)
        bucket = groups.get(key)
        if bucket is None:
            groups[key] = {
                "name": ingredient.food.food_name,
                "quantity": grams,
                "unit": "g",
                "food": ingredient.food,
            }
        else:
            bucket["quantity"] += grams
        return
    if ingredient.food_id is not None and unit:
        key = ("unit", ingredient.food_id, unit)
        bucket = groups.get(key)
        if bucket is None:
            groups[key] = {
                "name": ingredient.food.food_name,
                "quantity": amount,
                "unit": unit,
                "food": ingredient.food,
            }
        else:
            bucket["quantity"] += amount
        return
    loose.append(
        {
            "name": f"{ingredient.label} ({recipe_title})",
            "quantity": amount,
            "unit": ingredient.unit,
            "food": None,
        }
    )


def consumed_week(user, week_start: date) -> dict:
    """Totals from logged meals only. Planned recipes are ignored."""
    meal_count = 0
    days_with_meals = 0
    energy = Decimal("0")
    incomplete = False
    for offset in range(7):
        progress = get_daily_progress(user, week_start + timedelta(days=offset))
        count = progress["meal_count"]
        meal_count += count
        if count:
            days_with_meals += 1
            value = progress["consumed"]["energy_kcal"]
            if value is None:
                incomplete = True
            elif not incomplete:
                energy += value
    if meal_count == 0:
        status, energy_json = "empty", None
        note = "No meals have been logged this week."
    elif incomplete:
        status, energy_json = "incomplete", None
        note = "Weekly energy is omitted because a logged meal is missing an energy value."
    else:
        status, energy_json = "complete", str(energy)
        note = "Weekly energy counts logged meals only. Planned recipes are not included."
    return {
        "week_start": week_start.isoformat(),
        "days_with_meals": days_with_meals,
        "meal_count": meal_count,
        "energy_kcal": energy_json,
        "energy_status": status,
        "note": note,
    }


def home_payload(user) -> dict:
    today = timezone.now().date()
    week_start = monday(today)
    progress = get_daily_progress(user, today)
    from apps.targets.serializers import TargetSerializer
    from apps.targets.services import current_target

    target = current_target(user)
    saved = list(SavedRecipe.objects.filter(user=user).select_related("recipe")[:4])
    saved_ids = {row.recipe_id for row in saved}
    featured, featured_reason = _featured_recipe(user)
    grocery = grocery_for(user)
    preview = [
        _item_json(item)
        for item in grocery.items.select_related("food").filter(purchased=False)[:5]
    ]
    return {
        "name": user.name,
        "date": today.isoformat(),
        "today": {
            "meal_count": progress["meal_count"],
            "consumed": nutrient_json(progress["consumed"]),
            "remaining": None
            if progress["remaining"] is None
            else {name: None if value is None else str(value) for name, value in progress["remaining"].items()},
            "target": None if target is None else TargetSerializer(target).data,
        },
        "week": consumed_week(user, week_start),
        "groceries": {
            "outstanding_count": grocery.items.filter(purchased=False).count(),
            "items": preview,
        },
        "saved_recipes": [recipe_card(row.recipe, saved_ids) for row in saved],
        "featured": None if featured is None else recipe_detail(featured, user, featured.base_servings),
        "featured_reason": featured_reason,
    }


def _featured_recipe(user):
    saved = SavedRecipe.objects.filter(user=user).select_related("recipe")
    for row in saved:
        nutrition = recipe_nutrition(row.recipe, row.recipe.base_servings)
        if nutrition["status"] == "complete":
            return row.recipe, "Shown because it is saved and every ingredient has a verified calculation."
    for recipe in Recipe.objects.prefetch_related("ingredients__food"):
        nutrition = recipe_nutrition(recipe, recipe.base_servings)
        if nutrition["status"] == "complete":
            return recipe, "Shown because every ingredient has a verified calculation."
    if Recipe.objects.exists():
        return None, "No recipe has a complete verified calculation, so none is featured."
    return None, "No recipes are loaded yet."


def suggestions_payload(user) -> dict:
    today = timezone.now().date()
    progress = get_daily_progress(user, today)
    remaining = progress["remaining"]
    if remaining is None:
        gaps = None
        message = "No active nutrition target is stored, so these figures are calculated recipe amounts only."
    else:
        gaps = [
            {"nutrient": name, "remaining": None if remaining[name] is None else str(remaining[name]), "unit": unit}
            for name, unit in (
                ("calories", "kcal"),
                ("protein_g", "g"),
                ("carbohydrates_g", "g"),
                ("fat_g", "g"),
                ("fibre_g", "g"),
            )
        ]
        message = "Gaps compare today's logged meals with the active target. Planned meals are not included."
    ranked = []
    for recipe in Recipe.objects.prefetch_related("ingredients__food"):
        nutrition = recipe_nutrition(recipe, recipe.base_servings)
        if nutrition["status"] != "complete" or nutrition["nutrients"] is None:
            continue
        protein = nutrition["nutrients"]["protein_g"]
        ranked.append((Decimal(protein) if protein is not None else Decimal("-1"), recipe, nutrition))
    ranked.sort(key=lambda item: item[0], reverse=True)
    recipes = []
    protein_left = None if remaining is None else remaining["protein_g"]
    for _protein, recipe, nutrition in ranked[:3]:
        shown = nutrition["nutrients"]["protein_g"]
        if shown is None:
            protein_text = "an unknown amount of"
        else:
            protein_text = f"{Decimal(shown).quantize(Decimal('0.1')):f} g"
        reason = f"One base serving calculates to {protein_text} protein from verified ingredients."
        if protein_left is not None:
            reason += f" Today's remaining protein target is {protein_left} g."
        reason += " This is not a claim that the serving meets the daily goal."
        recipes.append(
            {
                "slug": recipe.slug,
                "title": recipe.title,
                "summary": recipe.summary,
                "reason": reason,
                "nutrition": nutrition,
            }
        )
    if not recipes:
        message += " No recipe has a complete verified calculation to show."
    return {"date": today.isoformat(), "gaps": gaps, "message": message, "recipes": recipes}


from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone
from openpyxl import Workbook
from rest_framework_simplejwt.tokens import RefreshToken

from apps.kitchen.models import GroceryItem, PlannedMeal, Recipe, RecipeIngredient
from apps.meals.models import Meal
from apps.nutrition.ingestion import load_nutrition
from apps.nutrition.nutrients import NUTRIENT_FIELDS

pytestmark = pytest.mark.django_db


def _auth(api_client, user):
    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client


def _headers():
    return (
        ["food_code", "food_name", "primarysource", "servings_unit"]
        + list(NUTRIENT_FIELDS)
        + [f"unit_serving_{name}" for name in NUTRIENT_FIELDS]
    )


def _food(**overrides):
    row = {name: 0 for name in NUTRIENT_FIELDS}
    row.update({f"unit_serving_{name}": None for name in NUTRIENT_FIELDS})
    row.update({"primarysource": "test", "servings_unit": ""})
    row.update(overrides)
    return row


def _load_foods(tmp_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    headers = _headers()
    sheet.append(headers)
    rows = [
        _food(food_code="RICE", food_name="Boiled rice", energy_kcal=130, protein_g=3),
        _food(food_code="EGG", food_name="Boiled egg", energy_kcal=155, protein_g=13, servings_unit="egg", unit_serving_energy_kcal=70, unit_serving_protein_g=6),
        _food(food_code="ASC113", food_name="Boiled rice", energy_kcal=130, protein_g=3),
    ]
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    path = tmp_path / "foods.xlsx"
    workbook.save(path)
    load_nutrition(path)


def _recipe(slug, food, quantity="100", unit="g", title="Rice bowl"):
    recipe = Recipe.objects.create(
        slug=slug,
        title=title,
        summary="A test recipe.",
        instructions="Serve it.",
        base_servings=Decimal("1"),
        source_name="Swasthya curated collection",
        source_note="Test recipe.",
        license_note="Test.",
    )
    RecipeIngredient.objects.create(
        recipe=recipe,
        food=food,
        label=food.food_name if food else "Fresh coriander leaves",
        quantity=Decimal(quantity),
        unit=unit,
        sort_order=0,
    )
    return recipe


def test_recipe_nutrition_scales_and_stays_incomplete_without_a_food(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    from apps.nutrition.models import Food

    rice = Food.objects.get(food_code="RICE")
    recipe = _recipe("rice-bowl", rice)
    incomplete = Recipe.objects.create(
        slug="coriander",
        title="Soup with coriander",
        summary="Missing herb.",
        instructions="Stir.",
        base_servings=Decimal("1"),
        source_name="Swasthya curated collection",
        source_note="Test.",
        license_note="Test.",
    )
    RecipeIngredient.objects.create(
        recipe=incomplete,
        food=rice,
        label="Boiled rice",
        quantity=Decimal("50"),
        unit="g",
    )
    RecipeIngredient.objects.create(
        recipe=incomplete,
        food=None,
        label="Fresh coriander leaves",
        quantity=Decimal("10"),
        unit="g",
        note="No matching verified food in the active dataset.",
    )
    user = make_user()
    _auth(api_client, user)

    assert api_client.get("/api/recipes/").status_code == 200
    detail = api_client.get("/api/recipes/rice-bowl/?servings=2").json()
    assert Decimal(detail["ingredients"][0]["quantity"]) == Decimal("200")
    assert detail["nutrition"]["status"] == "complete"
    assert Decimal(detail["nutrition"]["nutrients"]["energy_kcal"]) == Decimal("260")
    assert "meets" not in detail["source_note"]

    hidden = api_client.get("/api/recipes/coriander/").json()
    assert hidden["nutrition"]["status"] == "incomplete"
    assert hidden["nutrition"]["nutrients"] is None
    assert hidden["nutrition"]["missing"][0]["label"] == "Fresh coriander leaves"

    saved = api_client.post("/api/recipes/rice-bowl/save/")
    assert saved.status_code == 201
    assert api_client.get("/api/recipes/saved/").json()["results"][0]["slug"] == "rice-bowl"
    other = make_user(email="other@example.com")
    _auth(api_client, other)
    assert api_client.get("/api/recipes/saved/").json()["results"] == []
    assert api_client.get("/api/recipes/rice-bowl/").json()["saved"] is False


def test_planning_does_not_change_logged_nutrition(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    from apps.nutrition.models import Food

    rice = Food.objects.get(food_code="RICE")
    recipe = _recipe("rice-bowl", rice)
    user = make_user()
    _auth(api_client, user)
    day = timezone.now().date()
    created = api_client.post(
        "/api/plans/entries/",
        {"date": day.isoformat(), "slot": "lunch", "recipe_slug": recipe.slug, "servings": "1"},
        format="json",
    )
    assert created.status_code == 201
    assert Meal.objects.filter(user=user).count() == 0
    assert api_client.get("/api/dashboard/").json()["progress"]["meal_count"] == 0

    logged = api_client.post(
        "/api/meals/",
        {"meal_type": "breakfast", "items": [{"food_code": "RICE", "quantity": "100", "unit": "g"}]},
        format="json",
    )
    assert logged.status_code == 201
    dashboard = api_client.get("/api/dashboard/").json()
    assert dashboard["progress"]["meal_count"] == 1
    assert Decimal(dashboard["progress"]["consumed"]["energy_kcal"]) == Decimal("130")
    plan = api_client.get(f"/api/plans/?week={day.isoformat()}").json()
    assert len(plan["days"][day.weekday()]["slots"]["lunch"]) == 1
    assert Meal.objects.count() == 1

    other = make_user(email="planner-other@example.com")
    _auth(api_client, other)
    assert api_client.patch(f"/api/plans/entries/{created.json()['id']}/", {"servings": "2"}, format="json").status_code == 404


def test_grocery_generation_merges_only_compatible_rows_and_keeps_manual_items(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    from apps.nutrition.models import Food

    rice = Food.objects.get(food_code="RICE")
    egg = Food.objects.get(food_code="EGG")
    first = _recipe("rice-a", rice, quantity="100", unit="g", title="Rice A")
    second = _recipe("rice-b", rice, quantity="0.05", unit="kg", title="Rice B")
    eggs = _recipe("eggs", egg, quantity="1", unit="egg", title="Egg")
    grams = _recipe("egg-grams", egg, quantity="50", unit="g", title="Egg grams")
    loose = Recipe.objects.create(
        slug="herb",
        title="Herb",
        summary="Unmapped.",
        instructions="Add it.",
        base_servings=Decimal("1"),
        source_name="Swasthya curated collection",
        source_note="Test.",
        license_note="Test.",
    )
    RecipeIngredient.objects.create(recipe=loose, food=None, label="Fresh coriander leaves", quantity=Decimal("5"), unit="g")
    user = make_user()
    _auth(api_client, user)
    day = timezone.now().date()
    for slug, servings in ((first.slug, "1"), (second.slug, "1"), (eggs.slug, "2"), (grams.slug, "1"), (loose.slug, "1")):
        assert api_client.post(
            "/api/plans/entries/",
            {"date": day.isoformat(), "slot": "dinner", "recipe_slug": slug, "servings": servings},
            format="json",
        ).status_code == 201

    manual = api_client.post("/api/groceries/items/", {"name": "Salt", "quantity": "1", "unit": "pack"}, format="json")
    assert manual.status_code == 201
    generated = api_client.post("/api/groceries/generate/", {"week": day.isoformat()}, format="json")
    assert generated.status_code == 200
    items = generated.json()["items"]
    rice_rows = [item for item in items if item["food_code"] == "RICE"]
    assert len(rice_rows) == 1
    assert Decimal(rice_rows[0]["quantity"]) == Decimal("150")
    assert rice_rows[0]["unit"] == "g"
    egg_units = {item["unit"] for item in items if item["food_code"] == "EGG"}
    assert egg_units == {"egg", "g"}
    assert any(item["name"].startswith("Fresh coriander leaves") and item["food_code"] is None for item in items)
    assert any(item["name"] == "Salt" and item["origin"] == "manual" for item in items)

    again = api_client.post("/api/groceries/generate/", {"week": day.isoformat()}, format="json").json()["items"]
    assert sum(1 for item in again if item["origin"] == "generated" and item["food_code"] == "RICE") == 1
    assert sum(1 for item in again if item["origin"] == "manual") == 1

    salt = next(item for item in again if item["name"] == "Salt")
    marked = api_client.patch(f"/api/groceries/items/{salt['id']}/", {"purchased": True}, format="json")
    assert marked.status_code == 200
    assert marked.json()["purchased"] is True
    other = make_user(email="shopper@example.com")
    _auth(api_client, other)
    assert api_client.delete(f"/api/groceries/items/{salt['id']}/").status_code == 404
    assert GroceryItem.objects.filter(pk=salt["id"]).exists()
    assert PlannedMeal.objects.filter(plan__user=user).count() == 5


def test_catalogue_links_known_foods_and_leaves_unknown_ingredients_unmapped(tmp_path):
    _load_foods(tmp_path)
    call_command("load_recipes")
    rice = RecipeIngredient.objects.get(recipe__slug="moong-rice-bowl", label="Boiled rice")
    assert rice.food.food_code == "ASC113"
    herb = RecipeIngredient.objects.get(label="Fresh coriander leaves")
    assert herb.food_id is None
    assert Recipe.objects.get(slug="lentil-soup-coriander").source_name == "Swasthya curated collection"


def test_suggestions_use_logged_gaps_and_complete_recipes_only(api_client, make_user, tmp_path):
    _load_foods(tmp_path)
    from apps.nutrition.models import Food

    rice = Food.objects.get(food_code="RICE")
    _recipe("rice-bowl", rice, quantity="100", unit="g", title="Rice bowl")
    user = make_user(name="Asha")
    _auth(api_client, user)
    api_client.post(
        "/api/targets/customize/",
        {"calories": "2000", "protein_g": "80", "carbohydrates_g": "200", "fat_g": "60", "fibre_g": "25"},
        format="json",
    )
    api_client.post(
        "/api/meals/",
        {"meal_type": "breakfast", "items": [{"food_code": "RICE", "quantity": "100", "unit": "g"}]},
        format="json",
    )
    body = api_client.get("/api/suggestions/").json()
    assert body["gaps"] is not None
    assert "not a claim that the serving meets the daily goal" in body["recipes"][0]["reason"]
    home = api_client.get("/api/home/").json()
    assert home["name"] == "Asha"
    assert home["today"]["meal_count"] == 1
    assert home["week"]["energy_status"] == "complete"
    assert Decimal(home["week"]["energy_kcal"]) == Decimal("130")
    assert home["featured"]["nutrition"]["status"] == "complete"

    day = timezone.now().date()
    api_client.post(
        "/api/plans/entries/",
        {"date": day.isoformat(), "slot": "snack", "recipe_slug": "rice-bowl", "servings": "3"},
        format="json",
    )
    after_plan = api_client.get("/api/home/").json()
    assert Decimal(after_plan["week"]["energy_kcal"]) == Decimal("130")
    assert after_plan["today"]["meal_count"] == 1

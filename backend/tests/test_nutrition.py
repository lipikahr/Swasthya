from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook
from rest_framework_simplejwt.tokens import RefreshToken

from apps.nutrition.calculation import NutritionError, calculate_nutrition
from apps.nutrition.ingestion import IngestError, load_nutrition
from apps.nutrition.embeddings import EMBEDDING_MODEL
from apps.nutrition.models import Food, FoodEmbedding, FoodNutrition, FoodServingNutrition, NutritionDatasetVersion
from apps.nutrition.nutrients import NUTRIENT_FIELDS, WORKBOOK_NAME
from apps.nutrition.search import resolve_food

pytestmark = pytest.mark.django_db

REAL_WORKBOOK = Path(__file__).resolve().parents[2] / "data" / "raw" / WORKBOOK_NAME


def _headers():
    return (
        ["food_code", "food_name", "primarysource", "servings_unit", "vitb9_ug"]
        + list(NUTRIENT_FIELDS)
        + [f"unit_serving_{name}" for name in NUTRIENT_FIELDS]
    )


def _row(**overrides):
    row = {name: 0 for name in NUTRIENT_FIELDS}
    row.update({f"unit_serving_{name}": None for name in NUTRIENT_FIELDS})
    row.update(
        {
            "food_code": "T001",
            "food_name": "Test food",
            "primarysource": "test",
            "servings_unit": "",
            "vitb9_ug": 999,
        }
    )
    row.update(overrides)
    return row


def _write(path: Path, rows: list[dict]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    headers = _headers()
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header) for header in headers])
    workbook.save(path)


def test_blank_nutrient_stays_blank_and_is_not_treated_as_zero(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="A1", food_name="Plain rice", energy_kcal=100, fibre_g=None)])
    load_nutrition(path)

    nutrition = FoodNutrition.objects.get(food__food_code="A1")
    assert nutrition.energy_kcal == Decimal("100")
    assert nutrition.fibre_g is None
    assert nutrition.folate_ug == Decimal("0")

    result = calculate_nutrition("A1", 250, "g")
    assert result["basis"] == "per_100g"
    assert result["nutrients"]["energy_kcal"] == Decimal("250")
    assert result["nutrients"]["fibre_g"] is None


def test_known_zero_stays_zero(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(energy_kcal=80, fibre_g=0)])
    load_nutrition(path)
    result = calculate_nutrition("T001", Decimal("0.25"), "kg")
    assert result["unit"] == "kg"
    assert result["nutrients"]["energy_kcal"] == Decimal("200")
    assert result["nutrients"]["fibre_g"] == Decimal("0")


def test_folate_is_not_taken_from_vitb9(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(folate_ug=Decimal("4.5"), vitb9_ug=Decimal("80"))])
    load_nutrition(path)
    assert FoodNutrition.objects.get().folate_ug == Decimal("4.5")


def test_serving_numbers_without_a_unit_are_not_stored(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [_row(servings_unit="", unit_serving_energy_kcal=40, energy_kcal=10)],
    )
    report = load_nutrition(path)
    assert report.skipped_servings_without_unit == 1
    assert FoodServingNutrition.objects.count() == 0
    assert Food.objects.get().serving_unit == ""
    with pytest.raises(NutritionError) as caught:
        calculate_nutrition("T001", 1, "bowl")
    assert caught.value.code == "unsupported_unit"


def test_named_serving_uses_per_serving_values_and_not_a_gram_guess(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(
                food_code="IDLI",
                food_name="Idli",
                energy_kcal=100,
                servings_unit="piece",
                unit_serving_energy_kcal=40,
                unit_serving_fibre_g=None,
            )
        ],
    )
    load_nutrition(path)

    two_pieces = calculate_nutrition("IDLI", 2, "piece")
    assert two_pieces["basis"] == "per_serving"
    assert two_pieces["nutrients"]["energy_kcal"] == Decimal("80")
    assert two_pieces["nutrients"]["fibre_g"] is None

    by_weight = calculate_nutrition("IDLI", 50, "grams")
    assert by_weight["basis"] == "per_100g"
    assert by_weight["nutrients"]["energy_kcal"] == Decimal("50")

    with pytest.raises(NutritionError) as caught:
        calculate_nutrition("IDLI", 1, "bowl")
    assert caught.value.code == "unsupported_unit"


def test_duplicate_food_code_loads_nothing(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="DUP"), _row(food_code="DUP", food_name="Other")])
    with pytest.raises(IngestError):
        load_nutrition(path)
    assert Food.objects.count() == 0


def test_reload_updates_the_same_food(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(energy_kcal=10)])
    load_nutrition(path)
    _write(path, [_row(energy_kcal=20)])
    load_nutrition(path)
    assert Food.objects.count() == 1
    assert FoodNutrition.objects.get().energy_kcal == Decimal("20")


def test_resolve_food_does_not_guess_when_several_names_match(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(
        path,
        [
            _row(food_code="R1", food_name="Brown rice"),
            _row(food_code="R2", food_name="White rice"),
        ],
    )
    load_nutrition(path)
    assert resolve_food("R1")["status"] == "resolved"
    assert resolve_food("rice")["status"] == "ambiguous"
    assert resolve_food("missing dish")["status"] == "not_found"


def test_embedding_neighbors_ask_for_clarification_instead_of_logging(tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="IDLI", food_name="Idli")])
    load_nutrition(path)
    version = NutritionDatasetVersion.objects.get(is_active=True)
    vector = [0.0] * 384
    vector[0] = 1.0
    FoodEmbedding.objects.create(
        food=Food.objects.get(food_code="IDLI"),
        dataset_version=version,
        embedding=vector,
        text_representation="passage: Idli",
        language="mul",
        model_name=EMBEDDING_MODEL,
    )
    result = resolve_food("zzz-not-a-food", embed=lambda texts: [vector])
    assert result["status"] == "not_found"
    assert result["foods"] == []


def test_a_plural_name_uses_the_singular_record_before_vectors(tmp_path, monkeypatch):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="IDLI", food_name="Idli"), _row(food_code="RICE", food_name="Rice")])
    load_nutrition(path)
    version = NutritionDatasetVersion.objects.get(is_active=True)
    vector = [0.0] * 384
    vector[0] = 1.0
    FoodEmbedding.objects.create(
        food=Food.objects.get(food_code="RICE"),
        dataset_version=version,
        embedding=vector,
        text_representation="Rice",
        language="mul",
        model_name=EMBEDDING_MODEL,
    )
    monkeypatch.setattr(
        "apps.nutrition.embeddings.embed_texts",
        lambda texts: (_ for _ in ()).throw(AssertionError("the embedding model should not run")),
    )
    from apps.agent.workflow import _resolve_query

    result = _resolve_query("idlis")
    assert result["status"] == "resolved"
    assert result["food"].food_code == "IDLI"


def test_food_endpoints_require_a_token_and_return_stored_values(api_client, make_user, tmp_path):
    path = tmp_path / "foods.xlsx"
    _write(path, [_row(food_code="CHAI", food_name="Hot tea", energy_kcal=16, servings_unit="tea cup", unit_serving_energy_kcal=34)])
    load_nutrition(path)

    assert api_client.get("/api/foods/search/?q=tea").status_code == 401

    user = make_user()
    access = str(RefreshToken.for_user(user).access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    found = api_client.get("/api/foods/search/?q=tea")
    assert found.status_code == 200
    assert found.json()["results"][0]["food_code"] == "CHAI"

    detail = api_client.get("/api/foods/CHAI/")
    assert detail.status_code == 200
    body = detail.json()
    assert body["dataset_version"] == "anuvaad-indb-2024.11"
    assert body["nutrient_basis"] == "per_100g"
    assert Decimal(body["nutrients"]["energy_kcal"]) == Decimal("16")
    assert body["serving"]["unit"] == "tea cup"
    assert Decimal(body["serving"]["nutrients"]["energy_kcal"]) == Decimal("34")
    assert api_client.get("/api/foods/missing/").status_code == 404

    from apps.meals.models import Meal

    suggested = api_client.get("/api/foods/search/?q=tea&suggest=1&limit=5")
    assert suggested.status_code == 200
    names = [row["food_name"] for row in suggested.json()["results"]]
    assert names == ["Hot tea"]
    assert len(names) <= 5
    assert Meal.objects.count() == 0


@pytest.mark.skipif(not REAL_WORKBOOK.is_file(), reason="The Anuvaad workbook is local and is not in Git.")
def test_real_anuvaad_workbook_loads_without_inventing_servings():
    report = load_nutrition(REAL_WORKBOOK)
    assert report.foods == 1014
    assert report.serving_rows == 917
    assert report.skipped_servings_without_unit == 15

    tea = calculate_nutrition("ASC001", 1, "tea cup")
    assert tea["basis"] == "per_serving"
    assert tea["nutrients"]["energy_kcal"] != calculate_nutrition("ASC001", 100, "g")["nutrients"]["energy_kcal"]

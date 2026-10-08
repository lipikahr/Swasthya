"""Read the Anuvaad workbook and load it into PostgreSQL.

The workbook file is only read. Blank cells stay null. A serving row is stored
only when servings_unit is present, because the unit is the verified basis.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction
from openpyxl import load_workbook

from .models import Food, FoodNutrition, FoodServingNutrition, NutritionDatasetVersion
from .nutrients import (
    DATASET_CODE,
    DATASET_NAME,
    NUTRIENT_BASIS,
    NUTRIENT_FIELDS,
    WORKBOOK_NAME,
)

SERVING_UNIT_COLUMN = "servings_unit"
SOURCE_COLUMN = "primarysource"


class IngestError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class ParsedFood:
    food_code: str
    food_name: str
    primary_source: str
    nutrients: dict[str, Decimal | None]
    serving_unit: str
    serving_nutrients: dict[str, Decimal | None] | None


@dataclass
class IngestReport:
    foods: int = 0
    serving_rows: int = 0
    skipped_servings_without_unit: int = 0
    errors: list[str] = field(default_factory=list)


def default_workbook_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "raw" / WORKBOOK_NAME


def parse_workbook(path: Path) -> tuple[list[ParsedFood], IngestReport]:
    if not path.is_file():
        raise IngestError([f"Workbook not found: {path.name}"])

    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            raise IngestError(["The workbook has no header row."])
        columns = _header_index(header)
        _require_columns(columns)

        parsed: list[ParsedFood] = []
        report = IngestReport()
        seen: set[str] = set()
        for row_number, raw in enumerate(rows, start=2):
            if raw is None or all(cell is None or str(cell).strip() == "" for cell in raw):
                continue
            item, row_errors, skipped_serving = _parse_row(raw, columns, row_number)
            report.errors.extend(row_errors)
            if item is None:
                continue
            if item.food_code in seen:
                report.errors.append(f"Row {row_number}: duplicate food_code {item.food_code}.")
                continue
            seen.add(item.food_code)
            if skipped_serving:
                report.skipped_servings_without_unit += 1
            parsed.append(item)
        if report.errors:
            raise IngestError(report.errors[:20])
        return parsed, report
    finally:
        workbook.close()


def load_nutrition(path: Path | None = None) -> IngestReport:
    workbook_path = path or default_workbook_path()
    foods, report = parse_workbook(workbook_path)
    with transaction.atomic():
        version, _ = NutritionDatasetVersion.objects.update_or_create(
            code=DATASET_CODE,
            defaults={
                "name": DATASET_NAME,
                "source_filename": workbook_path.name,
                "nutrient_basis": NUTRIENT_BASIS,
                "is_active": True,
            },
        )
        NutritionDatasetVersion.objects.exclude(pk=version.pk).update(is_active=False)
        for item in foods:
            food, _ = Food.objects.update_or_create(
                food_code=item.food_code,
                defaults={
                    "food_name": item.food_name,
                    "primary_source": item.primary_source,
                    "serving_unit": item.serving_unit,
                },
            )
            FoodNutrition.objects.update_or_create(
                food=food,
                dataset_version=version,
                defaults=item.nutrients,
            )
            if item.serving_nutrients is None:
                FoodServingNutrition.objects.filter(food=food, dataset_version=version).delete()
            else:
                FoodServingNutrition.objects.update_or_create(
                    food=food,
                    dataset_version=version,
                    defaults={"serving_unit": item.serving_unit, **item.serving_nutrients},
                )
        report.foods = len(foods)
        report.serving_rows = sum(item.serving_nutrients is not None for item in foods)
    return report


def _header_index(header) -> dict[str, int]:
    columns: dict[str, int] = {}
    for index, name in enumerate(header):
        if name is None:
            continue
        columns[str(name).strip()] = index
    return columns


def _require_columns(columns: dict[str, int]) -> None:
    required = ["food_code", "food_name", SOURCE_COLUMN, SERVING_UNIT_COLUMN, *NUTRIENT_FIELDS]
    missing = [name for name in required if name not in columns]
    serving_missing = [
        f"unit_serving_{name}" for name in NUTRIENT_FIELDS if f"unit_serving_{name}" not in columns
    ]
    missing.extend(serving_missing)
    if missing:
        raise IngestError([f"Workbook is missing columns: {', '.join(missing)}"])


def _parse_row(raw, columns, row_number: int) -> tuple[ParsedFood | None, list[str], bool]:
    errors: list[str] = []
    food_code = _text(_cell(raw, columns, "food_code"))
    food_name = _text(_cell(raw, columns, "food_name"))
    if not food_code:
        errors.append(f"Row {row_number}: food_code is required.")
    if not food_name:
        errors.append(f"Row {row_number}: food_name is required.")

    nutrients, nutrient_errors = _nutrients(raw, columns, row_number, prefix="")
    errors.extend(nutrient_errors)
    serving_unit = _text(_cell(raw, columns, SERVING_UNIT_COLUMN))
    serving_values, serving_errors = _nutrients(raw, columns, row_number, prefix="unit_serving_")
    errors.extend(serving_errors)
    if errors:
        return None, errors, False

    skipped_serving = False
    serving_nutrients = None
    if serving_unit:
        serving_nutrients = serving_values
    elif any(value is not None for value in serving_values.values()):
        # Numbers without a unit are not a verified serving basis.
        skipped_serving = True

    return (
        ParsedFood(
            food_code=food_code,
            food_name=food_name,
            primary_source=_text(_cell(raw, columns, SOURCE_COLUMN)),
            nutrients=nutrients,
            serving_unit=serving_unit,
            serving_nutrients=serving_nutrients,
        ),
        [],
        skipped_serving,
    )


def _nutrients(raw, columns, row_number: int, prefix: str) -> tuple[dict[str, Decimal | None], list[str]]:
    values: dict[str, Decimal | None] = {}
    errors: list[str] = []
    for name in NUTRIENT_FIELDS:
        column = f"{prefix}{name}"
        cell = _cell(raw, columns, column)
        if cell is None or (isinstance(cell, str) and cell.strip() == ""):
            values[name] = None
            continue
        try:
            values[name] = Decimal(str(cell))
        except (InvalidOperation, ValueError):
            errors.append(f"Row {row_number}: {column} is not a number.")
            values[name] = None
    return values, errors


def _cell(raw, columns, name: str):
    index = columns[name]
    if index >= len(raw):
        return None
    return raw[index]


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

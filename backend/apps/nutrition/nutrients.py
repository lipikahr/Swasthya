"""Nutrient fields the product stores and calculates.

The names match the Anuvaad workbook. folate_ug is read from the folate_ug
column. vitb9_ug is a separate column in the sheet and is not added to folate.
"""

NUTRIENT_FIELDS = (
    "energy_kcal",
    "carb_g",
    "protein_g",
    "fat_g",
    "fibre_g",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "potassium_mg",
    "sodium_mg",
    "zinc_mg",
    "vita_ug",
    "vitb1_mg",
    "vitb2_mg",
    "vitb3_mg",
    "vitb6_mg",
    "folate_ug",
    "vitc_mg",
    "vitd2_ug",
    "vitd3_ug",
    "vite_mg",
    "vitk1_ug",
    "vitk2_ug",
)

DATASET_CODE = "anuvaad-indb-2024.11"
DATASET_NAME = "Anuvaad INDB 2024.11"
NUTRIENT_BASIS = "per_100g"
CALCULATION_VERSION = "swasthya-calc-v1"
WORKBOOK_NAME = "Anuvaad_INDB_2024.11.xlsx"

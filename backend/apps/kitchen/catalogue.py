"""Original Swasthya recipes.

Amounts and instructions were written for this project. They are not copied
from a cookbook and they are not Anuvaad records. A food_code is attached only
when that code exists in the verified dataset. An ingredient without a code
stays unmapped, and its recipe nutrition stays incomplete.
"""

SOURCE_NAME = "Swasthya curated collection"
SOURCE_NOTE = (
    "Recipe text and amounts were written for Swasthya. "
    "Anuvaad INDB 2024.11 is used only when an ingredient names one of its foods. "
    "The dataset does not supply these instructions or ingredient lists."
)
LICENSE_NOTE = (
    "Original recipe text in this repository. "
    "Calculated nutrition comes from Anuvaad INDB 2024.11 through the Swasthya nutrition service. "
    "It is not a published recipe nutrition label."
)

CATALOGUE = [
    {
        "slug": "moong-rice-bowl",
        "title": "Moong and rice bowl",
        "summary": "A two-serving bowl of boiled rice and moong dal.",
        "instructions": (
            "Warm the boiled rice and the moong dal. "
            "Spoon them into a bowl and serve while hot."
        ),
        "base_servings": "2",
        "ingredients": [
            {"label": "Boiled rice", "food_code": "ASC113", "quantity": "200", "unit": "g"},
            {"label": "Dal moong", "food_code": "BFP166", "quantity": "160", "unit": "g"},
        ],
    },
    {
        "slug": "rice-with-egg",
        "title": "Rice with a boiled egg",
        "summary": "Boiled rice served with one boiled egg.",
        "instructions": "Warm the boiled rice. Place the boiled egg beside it and serve.",
        "base_servings": "1",
        "ingredients": [
            {"label": "Boiled rice", "food_code": "ASC113", "quantity": "150", "unit": "g"},
            {"label": "Boiled egg", "food_code": "ASC056", "quantity": "1", "unit": "egg"},
        ],
    },
    {
        "slug": "breakfast-poha",
        "title": "Poha",
        "summary": "A single serving of poha from the verified food list.",
        "instructions": "Warm the poha through and serve it as one plate.",
        "base_servings": "1",
        "ingredients": [
            {"label": "Poha", "food_code": "BFP044", "quantity": "180", "unit": "g"},
        ],
    },
    {
        "slug": "oats-and-egg",
        "title": "Oats with a boiled egg",
        "summary": "Oatmeal porridge with one boiled egg.",
        "instructions": "Warm the oatmeal porridge. Serve it with the boiled egg.",
        "base_servings": "1",
        "ingredients": [
            {"label": "Oatmeal porridge", "food_code": "ASC050", "quantity": "250", "unit": "g"},
            {"label": "Boiled egg", "food_code": "ASC056", "quantity": "1", "unit": "egg"},
        ],
    },
    {
        "slug": "green-gram-bowl",
        "title": "Green gram bowl",
        "summary": "A two-serving bowl of cooked green gram.",
        "instructions": "Warm the green gram and divide it between two bowls.",
        "base_servings": "2",
        "ingredients": [
            {
                "label": "Green gram",
                "food_code": "BFP178",
                "quantity": "240",
                "unit": "g",
            },
        ],
    },
    {
        "slug": "lentil-soup-coriander",
        "title": "Lentil soup with coriander",
        "summary": "Lentil soup finished with fresh coriander. The herb is not a verified food match.",
        "instructions": (
            "Warm the lentil soup. "
            "Stir in the coriander just before serving. "
            "The coriander has no verified food match, so the recipe nutrition stays incomplete."
        ),
        "base_servings": "2",
        "ingredients": [
            {"label": "Lentil soup", "food_code": "ASC080", "quantity": "300", "unit": "g"},
            {
                "label": "Fresh coriander leaves",
                "food_code": None,
                "quantity": "10",
                "unit": "g",
                "note": "No matching verified food in the active dataset.",
            },
        ],
    },
]

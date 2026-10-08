from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.nutrition.embeddings import EMBEDDING_MODEL, embed_texts, passage_text
from apps.nutrition.ingestion import default_workbook_path
from apps.nutrition.models import FoodEmbedding, FoodNutrition, NutritionDatasetVersion


class Command(BaseCommand):
    help = "Create pgvector embeddings for food names in the active dataset."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=64)

    def handle(self, *args, **options):
        version = NutritionDatasetVersion.objects.filter(is_active=True).first()
        if version is None:
            raise CommandError("Load the nutrition workbook before creating embeddings.")
        rows = list(
            FoodNutrition.objects.filter(dataset_version=version).select_related("food").order_by("food__food_code")
        )
        batch_size = options["batch_size"]
        stored = 0
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            vectors = embed_texts([passage_text(item.food.food_name) for item in batch])
            with transaction.atomic():
                for item, vector in zip(batch, vectors):
                    FoodEmbedding.objects.update_or_create(
                        food=item.food,
                        dataset_version=version,
                        model_name=EMBEDDING_MODEL,
                        defaults={
                            "embedding": vector,
                            "text_representation": passage_text(item.food.food_name),
                            "language": "mul",
                        },
                    )
                    stored += 1
            self.stdout.write(f"Embedded {stored} of {len(rows)} foods.")
        self.stdout.write(f"Stored {stored} embeddings with {EMBEDDING_MODEL}.")
        if not Path(default_workbook_path()).is_file():
            self.stdout.write("The source workbook is not in data/raw; embeddings used the rows already in PostgreSQL.")

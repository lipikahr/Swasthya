from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.nutrition.ingestion import IngestError, default_workbook_path, load_nutrition


class Command(BaseCommand):
    help = "Load the read-only Anuvaad workbook into the nutrition tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help="Workbook path. Defaults to data/raw/Anuvaad_INDB_2024.11.xlsx.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]) if options["path"] else default_workbook_path()
        try:
            report = load_nutrition(path)
        except IngestError as exc:
            raise CommandError("\n".join(exc.errors)) from exc
        self.stdout.write(
            f"Loaded {report.foods} foods and {report.serving_rows} serving rows "
            f"from {path.name}."
        )
        if report.skipped_servings_without_unit:
            self.stdout.write(
                f"Skipped {report.skipped_servings_without_unit} serving rows "
                "because servings_unit was missing."
            )

from django.core.management.base import BaseCommand

from apps.kitchen.services import load_catalogue


class Command(BaseCommand):
    help = "Load the Swasthya curated recipe collection and link ingredients to verified foods when the code exists."

    def handle(self, *args, **options):
        report = load_catalogue()
        self.stdout.write(
            f"Loaded {report['recipes']} recipes. "
            f"Mapped {report['mapped_ingredients']} ingredients. "
            f"Left {report['unmapped_ingredients']} ingredients without a verified food."
        )

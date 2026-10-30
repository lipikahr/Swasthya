from django.core.management.base import BaseCommand, CommandError

from apps.agent.providers import probe_gemini


class Command(BaseCommand):
    help = "Report whether GEMINI_API_KEY is configured and attempt one Gemini request. Never prints the key."

    def handle(self, *args, **options):
        result = probe_gemini()
        self.stdout.write(f"key_configured={result['key_configured']}")
        self.stdout.write(f"provider={result['provider']}")
        self.stdout.write(f"model={result['model']}")
        self.stdout.write(f"live_request={result['live_request']}")
        if result.get("error_class"):
            self.stdout.write(f"error_class={result['error_class']}")
        if result.get("message"):
            self.stdout.write(result["message"])
        if result.get("extracted_item_count") is not None:
            self.stdout.write(f"extracted_item_count={result['extracted_item_count']}")
        if not result["ok"]:
            raise CommandError(result.get("message") or "Gemini check failed.")

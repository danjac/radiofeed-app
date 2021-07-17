from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up initial categories and sample podcasts."

    def handle(self, *args, **options) -> None:
        fixtures_dir = settings.BASE_DIR / "jcasts" / "podcasts" / "fixtures"
        for filename in ("categories.json.gz", "podcasts.json.gz"):
            call_command("loaddata", fixtures_dir / filename)

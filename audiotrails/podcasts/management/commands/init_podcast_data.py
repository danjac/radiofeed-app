from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sets up initial categories and sample podcasts."

    def handle(self, *args, **kwargs):
        fixtures_dir = settings.BASE_DIR / "audiotrails" / "podcasts" / "fixtures"
        call_command("loaddata", fixtures_dir / "categories.json.gz")
        call_command("loaddata", fixtures_dir / "podcasts.json.gz")

from django.core.management.base import BaseCommand

from jcasts.podcasts import websub


class Command(BaseCommand):
    help = "Subscribe podcasts to websub"

    def handle(self, *args, **options):
        num_feeds = websub.subscribe_podcasts()
        self.stdout.write(
            self.style.SUCCESS(f"Subscribe requests queued for {num_feeds} feed(s)")
        )

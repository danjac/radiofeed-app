from django.core.management.base import BaseCommand

from jcasts.podcasts import websub


class Command(BaseCommand):
    help = "Subscribe podcasts to websub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--retry",
            action="store_true",
            help="Retry any failed subscribe requests",
        )

    def handle(self, *args, **options):
        num_feeds = websub.subscribe_podcasts(retry=options["retry"])
        self.stdout.write(
            self.style.SUCCESS(f"Subscribe requests queued for {num_feeds} feed(s)")
        )

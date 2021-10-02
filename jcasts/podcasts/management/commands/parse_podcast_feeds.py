from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Run podcast feed updates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Podcast.objects.update(queued=None)
        jobs = [*feed_parser.parse_podcast_feeds()]
        self.stdout.write(self.style.SUCCESS(f"{len(jobs)} feed(s) to be pulled"))

# Django
from django.core.management.base import BaseCommand

# RadioFeed
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import sync_podcast_feed


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def add_arguments(self, parser):

        parser.add_argument(
            "--no-pub-date",
            action="store_true",
            help="Updates only podcasts without a pub date",
        )

    def handle(self, *args, **options):
        podcasts = Podcast.objects.all()

        if options["no_pub_date"]:
            podcasts = podcasts.filter(pub_date__isnull=True)

        for podcast in podcasts:
            self.stdout.write(f"Syncing podcast {podcast}")
            sync_podcast_feed.delay(podcast_id=podcast.id)

# Django
from django.core.management.base import BaseCommand

# RadioFeed
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.rss_parser import RssParser
from radiofeed.podcasts.tasks import sync_podcast_feed


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def add_arguments(self, parser):

        parser.add_argument(
            "--no-pub-date",
            action="store_true",
            help="Updates only podcasts without a pub date",
        )

        parser.add_argument(
            "--use-celery",
            action="store_true",
            help="Sync each podcast using celery task",
        )

    def handle(self, *args, **options):
        podcasts = Podcast.objects.all()

        if options["no_pub_date"]:
            podcasts = podcasts.filter(pub_date__isnull=True)

        for podcast in podcasts:
            self.stdout.write(f"Syncing podcast {podcast}")
            if options["use_celery"]:
                sync_podcast_feed.delay(podcast_id=podcast.id)
            else:
                try:
                    new_episodes = RssParser.parse_from_podcast(podcast)
                    if new_episodes:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{podcast.title}: {len(new_episodes)} new episode(s)"
                            )
                        )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(e))

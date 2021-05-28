from django.core.management.base import BaseCommand, CommandParser

from audiotrails.podcasts.feed_parser import parse_feed
from audiotrails.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Updates single podcast feed"

    def add_arguments(self, parser: CommandParser) -> None:

        parser.add_argument("podcast_id", type=int)

    def handle(self, **options) -> None:
        try:
            podcast = Podcast.objects.get(pk=options["podcast_id"])
            new_episodes = parse_feed(podcast)
            if new_episodes:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{len(new_episodes)} new episodes for podcast {podcast.title}"
                    )
                )
            else:
                self.stdout.write(f"No new episodes for podcast {podcast.title}")

        except Podcast.DoesNotExist:
            self.stderr.write(self.style.ERROR("No podcast found matching this ID"))

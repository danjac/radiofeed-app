import requests

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from audiotrails.podcasts.models import Podcast
from audiotrails.podcasts.rss_parser import RssParserError, parse_feed_from_url


class Command(BaseCommand):
    help = "Updates single podcast cover image"

    def add_arguments(self, parser: CommandParser) -> None:

        parser.add_argument("podcast_id", type=int)

        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update",
        )

    def handle(self, **options) -> None:
        try:
            podcast = Podcast.objects.get(pk=options["podcast_id"])
            feed = parse_feed_from_url(podcast.rss)

            if feed.should_update_image(
                podcast, force_update=options["force_update"]
            ) and (image := feed.fetch_cover_image()):

                podcast.cover_image = image
                podcast.cover_image_date = timezone.now()
                podcast.save()

                self.stdout.write(self.style.SUCCESS("Image updated"))
            else:
                self.stdout.write("No new image found")

        except requests.RequestException:
            self.stderr.write(
                self.style.ERROR("Unable to fetch RSS feed or image from network")
            )
        except Podcast.DoesNotExist:
            self.stderr.write(self.style.ERROR("No podcast found matching this ID"))
        except RssParserError as e:
            self.stderr.write(self.style.ERROR(f"RSS parser error: {e}"))

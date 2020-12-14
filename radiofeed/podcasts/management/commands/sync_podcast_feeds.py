# Django
from django.core.management.base import BaseCommand

# RadioFeed
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.rss_parser import RssParser


class Command(BaseCommand):
    help = "Updates all podcasts from their RSS feeds."

    def add_arguments(self, parser):

        parser.add_argument(
            "--no-pub-date",
            action="store_true",
            help="Updates only podcasts without a pub date",
        )

    def handle(self, *args, **options):
        total_num_episodes = 0
        podcasts = Podcast.objects.all()

        if options["no_pub_date"]:
            podcasts = podcasts.filter(pub_date__isnull=True)

        for podcast in podcasts:
            self.stdout.write(f"Syncing podcast {podcast}")
            try:
                new_episodes = RssParser.parse_from_podcast(podcast)
                if new_episodes:
                    num_episodes = len(new_episodes)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{num_episodes} new episode(s) added to podcast {podcast}"
                        )
                    )
                    total_num_episodes += num_episodes
            except Exception as e:
                self.stderr.write(str(e))
        self.stdout.write(
            self.style.SUCCESS(f"{total_num_episodes} total new episode(s) added")
        )

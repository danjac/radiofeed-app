from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Count

from audiotrails.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Removes all podcasts with no episodes or pub date"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def handle(self, **options) -> None:

        podcasts = Podcast.objects.annotate(num_episodes=Count("episode")).filter(
            num_episodes=0
        )

        num_podcasts = podcasts.count()

        if num_podcasts == 0:
            self.stderr.write("No dead podcasts found, exiting...")
            return

        self.stdout.write(f"{num_podcasts} dead podcasts found")

        if options["interactive"]:
            answer: str | None = None
            while answer not in "yn":
                answer = input("Do you wish to proceed? [yN] ")
                if not answer:
                    answer = "n"
                    break
                else:
                    answer = answer[0].lower()
            if answer != "y":
                return

        podcasts.delete()

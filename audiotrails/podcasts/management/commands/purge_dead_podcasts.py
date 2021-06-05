from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from audiotrails.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Removes all podcasts with no episodes or pub date"
    require_system_checks = False

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def handle(self, **options) -> None:

        podcasts = Podcast.objects.filter(pub_date__isnull=True)

        num_podcasts = podcasts.count()

        if num_podcasts == 0:
            self.stderr.write("No dead podcasts found, exiting...")
            return

        self.stdout.write(f"{num_podcasts} dead podcasts found")
        if self.handle_interactive(options["interactive"]):
            podcasts.delete()

    def handle_interactive(self, interactive: bool) -> bool:
        if not interactive:
            return True
        answer: str | None = None
        while answer is None or answer not in "yn":
            answer = (input("Do you wish to proceed? [yN] ") or "n")[:1].lower()
        return answer == "y"

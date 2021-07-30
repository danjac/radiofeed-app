from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler


class Command(BaseCommand):
    help = "Schedule podcast feeds for update"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="Reset all scheduled times"
        )

    def handle(self, *args, **options) -> None:
        if num_freq := scheduler.calc_podcast_frequencies(reset=options["reset"]):
            self.stdout.write(self.style.SUCCESS(f"{num_freq} podcast frequencies set"))

        if num_scheduled := scheduler.schedule_podcast_feeds(reset=options["reset"]):
            self.stdout.write(self.style.SUCCESS(f"{num_scheduled} podcasts scheduled"))

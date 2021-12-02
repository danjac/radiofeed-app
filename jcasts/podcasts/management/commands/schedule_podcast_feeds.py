from __future__ import annotations

import argparse

from django.core.management.base import BaseCommand

from jcasts.podcasts import scheduler
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds. Run this once to reset all podcast frequencies."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Tells Django to NOT prompt the user for input of any kind.",
        )

    def handle(self, *args, **options) -> None:
        if not self.should_execute(options["interactive"]):
            return

        podcasts = Podcast.objects.active().order_by("-pub_date")
        self.stdout.write(f"Scheduling {podcasts.count()} podcasts...")

        for_update: list[Podcast] = []

        for counter, podcast in enumerate(podcasts.iterator()):

            podcast.frequency = scheduler.schedule(
                list(podcast.episode_set.values_list("pub_date", flat=True))
            )

            self.stdout.write(f"{counter}: {podcast.title}: {podcast.frequency}")

            for_update.append(podcast)

        Podcast.objects.bulk_update(for_update, fields=["frequency"], batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduling complete, {len(for_update)} podcasts rescheduled."
            )
        )

    def should_execute(self, interactive: bool) -> bool:
        if not interactive:
            return True
        answer: str = ""
        while not answer or answer not in "yn":
            answer = input(
                self.style.WARNING(
                    "Will reset all frequencies!!! Do you wish to proceed? [yN] "
                )
            )
            if answer and answer[0].lower() != "y":
                self.stdout.write("Existing, no changes will be made.")
                return False
        return True

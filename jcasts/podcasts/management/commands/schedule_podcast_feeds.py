from __future__ import annotations

import argparse

from datetime import timedelta

from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--frequency", help="Frequency between updates (minutes)", default=60
        )

        parser.add_argument(
            "--reschedule", help="Reschedule all podcasts", action="store_true", default=False
        )

    def handle(self, *args, **options) -> None:
        if options["reschedule"]:
            self.reschedule()
        else:
            feed_parser.schedule_podcast_feeds(timedelta(minutes=options["frequency"]))

    def reschedule(self) -> None:
        for_update = []
        for podcast in Podcast.objects.active().published().iterator():
            pub_dates = list(Episode.objects.filter(podcast=podcast).values_list("pub_date", flat=True))
            podcast.frequency = feed_parser.get_frequency(pub_dates)
            podcast.scheduled = feed_parser.reschedule(podcast.frequency, podcast.pub_date)
            for_update.append(podcast)
        Podcast.objects.bulk_update(for_update, fields=["frequency", "scheduled"])
        
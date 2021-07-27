from django.core.management.base import BaseCommand

from jcasts.podcasts.feed_parser import calc_frequency
from jcasts.podcasts.models import Podcast


class Command(BaseCommand):
    help = "One-off command to set starting frequencies for all podcasts"

    def handle(self, *args, **options) -> None:
        qs = Podcast.objects.filter(
            pub_date__isnull=False, active=True, frequency=1
        ).order_by("-pub_date")
        total = qs.count()

        for counter, podcast in enumerate(qs.iterator(), 1):
            self.handle_podcast(podcast, counter, total)

    def handle_podcast(self, podcast, counter, total):
        pub_dates = podcast.episode_set.values_list("pub_date", flat=True).order_by(
            "-pub_date"
        )
        frequency = calc_frequency(pub_dates)
        Podcast.objects.filter(pk=podcast.id).update(frequency=frequency)
        self.stdout.write(f"[{counter}/{total}] Podcast {podcast}: freq {frequency}")

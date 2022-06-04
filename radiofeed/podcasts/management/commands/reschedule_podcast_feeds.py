from django.core.management.base import BaseCommand

from radiofeed.episodes.models import Episode
from radiofeed.podcasts import scheduler
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    help = """
    Reschedules refresh intervals of podcasts
    """

    def handle(self, *args, **kwargs) -> None:
        for counter, podcast in enumerate(
            Podcast.objects.filter(active=True).iterator()
        ):
            self.stdout.write(f"{counter}: {podcast.title}")
            podcast.refresh_interval = scheduler.calculate_refresh_interval(
                list(
                    Episode.objects.filter(podcast=podcast).values_list(
                        "pub_date", flat=True
                    )
                )
            )
            podcast.save(update_fields=["refresh_interval"])

import itertools
from datetime import datetime

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.template.defaultfilters import pluralize, timesince
from django.utils import timezone

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription


class Command(BaseCommand):
    """Command implementation."""

    help = "Removes old podcast content"

    prompt = (
        "This command will delete podcasts that are no longer active or have "
        "a publication date older than {since}. It will not remove "
        "podcasts that have bookmarks, listening history, or subscriptions. "
        "Are you sure you want to proceed? (Y/n) "
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command."""

        parser.add_argument(
            "--noinput",
            "-n",
            help="Do not prompt for input of any kind",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "--days-since",
            "-d",
            type=int,
            help="Delete podcasts last updated since",
            default=365,
        )

        parser.add_argument(
            "--batch_size",
            "-b",
            type=int,
            help="Number of podcasts to delete in each batch",
            default=100,
        )

    def handle(
        self,
        *,
        noinput: bool,
        days_since: int,
        batch_size: int,
        **options,
    ) -> None:
        """Removes podcasts:

        - no longer active
        - pub date older than number of days

        Does not remove podcasts having:

        - Bookmarks
        - Listening history
        - Subscriptions
        """
        since = timezone.now() - timezone.timedelta(days=days_since)
        if noinput or input(self.prompt.format(since=timesince(since))).lower() == "y":
            podcasts = self._get_queryset(since)
            if num_podcasts := podcasts.count():
                self.stdout.write(
                    f"Deleting {num_podcasts} inactive podcast{pluralize(num_podcasts)}..."
                )
                self._delete_podcasts(podcasts, batch_size, num_podcasts)
                self.stdout.write(
                    self.style.SUCCESS(f"{num_podcasts} inactive podcasts removed.")
                )
            else:
                self.stdout.write("No old podcasts found to remove.")

    def _get_queryset(self, since: datetime) -> QuerySet["Podcast"]:
        return Podcast.objects.alias(
            has_audio_logs=Exists(
                AudioLog.objects.filter(episode__podcast=OuterRef("pk")),
            ),
            has_bookmarks=Exists(
                Bookmark.objects.filter(episode__podcast=OuterRef("pk")),
            ),
            has_subscriptions=Exists(
                Subscription.objects.filter(podcast=OuterRef("pk")),
            ),
        ).filter(
            Q(active=False) | Q(pub_date__lt=since),
            has_audio_logs=False,
            has_bookmarks=False,
            has_subscriptions=False,
        )

    def _delete_podcasts(
        self,
        queryset: QuerySet["Podcast"],
        batch_size: int,
        num_podcasts: int,
    ) -> None:
        done = 0
        for batch in itertools.batched(
            queryset.values_list("pk", flat=True).iterator(),
            batch_size,
            strict=False,
        ):
            with transaction.atomic():
                queryset.filter(pk__in=set(batch)).delete()
                done += len(batch)
                pc_done = int(min(done / num_podcasts * 100, 100))
                self.stdout.write(f"{pc_done}% done")

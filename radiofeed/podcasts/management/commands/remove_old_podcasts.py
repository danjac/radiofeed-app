from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription


class Command(BaseCommand):
    """Command implementation."""

    help = "Removes old podcast content"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the command."""

        parser.add_argument(
            "--noinput",
            help="Do not prompt for input of any kind",
            action="store_true",
            default=False,
        )

    def handle(self, *, noinput=False, **options) -> None:
        """Removes podcasts:

        - no longer active
        - pub date older than 1 year

        Does not remove podcasts having:

        - Bookmarks
        - Listening history
        - Subscriptions
        """
        if self._confirm_removal(noinput=noinput):
            podcasts = self._get_queryset()
            if num_podcasts := podcasts.count():
                podcasts.delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{num_podcasts} old podcasts removed.",
                    )
                )
            else:
                self.stdout.write("No old podcasts found to remove.")

    def _confirm_removal(self, *, noinput: bool) -> bool:
        return noinput or (
            input(
                "This command will remove old podcasts that are no longer active "
                "or have a publication date older than one year. It will not remove "
                "podcasts that have bookmarks, listening history, or subscriptions. "
                "Are you sure you want to proceed? (Y/n) "
            ).lower()
            == "y"
        )

    def _get_queryset(self) -> QuerySet["Podcast"]:
        return Podcast.objects.alias(
            has_audio_logs=Exists(
                AudioLog.objects.filter(episode__podcast=OuterRef("id")),
            ),
            has_bookmarks=Exists(
                Bookmark.objects.filter(episode__podcast=OuterRef("id")),
            ),
            has_subscriptions=Exists(
                Subscription.objects.filter(podcast=OuterRef("id")),
            ),
        ).filter(
            Q(active=False)
            | Q(pub_date__lt=timezone.now() - timezone.timedelta(days=365)),
            has_audio_logs=False,
            has_bookmarks=False,
            has_subscriptions=False,
        )

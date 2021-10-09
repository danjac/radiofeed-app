from django.core.management.base import BaseCommand

from jcasts.podcasts import feed_parser


class Command(BaseCommand):
    help = "Schedule podcast feeds"

    def add_arguments(self, parser):
        parser.add_argument("--sporadic", action="store_true", default=False)
        parser.add_argument("--reschedule", action="store_true", default=False)
        parser.add_argument("--clearqueue", action="store_true", default=False)

    def handle(self, *args, **options):
        if options["clearqueue"]:
            feed_parser.clear_podcast_feed_queues()

        if options["reschedule"]:
            feed_parser.reschedule_podcast_feeds()
            return

        if options["sporadic"]:
            feed_parser.schedule_sporadic_podcast_feeds()
            return

        feed_parser.schedule_frequent_podcast_feeds()

# Django
from django.core.management.base import BaseCommand

# RadioFeed
from radiofeed.podcasts.recommender import PodcastRecommender


class Command(BaseCommand):
    help = "Creates new podcast recommendations."

    def handle(self, *args, **kwargs):
        PodcastRecommender.recommend()

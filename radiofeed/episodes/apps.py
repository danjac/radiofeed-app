# Django
from django.apps import AppConfig


class EpisodesConfig(AppConfig):
    name = "radiofeed.episodes"

    def ready(self):
        from . import signals  # noqa

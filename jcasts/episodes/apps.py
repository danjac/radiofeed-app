from django.apps import AppConfig


class EpisodesConfig(AppConfig):
    name = "jcasts.episodes"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self, **kwargs):
        import jcasts.episodes.signals  # noqa

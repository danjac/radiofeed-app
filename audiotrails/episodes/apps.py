from django.apps import AppConfig


class EpisodesConfig(AppConfig):
    name = "audiotrails.episodes"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from audiotrails.episodes import signals  # noqa

from django.apps import AppConfig


class PodcastsConfig(AppConfig):
    name = "audiotrails.podcasts"
    default_auto_field = "django.db.models.BigAutoField"

    from audiotrails.podcasts import signals  # noqa

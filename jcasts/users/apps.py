from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "jcasts.users"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self, **kwargs):
        import jcasts.users.signals  # noqa

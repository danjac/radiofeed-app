import os


def main() -> None:
    """Runs scheduler.

    Should search all `INSTALLED_APPS` for a `tasks` module which should have scheduled jobs.
    """

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.utils.module_loading import autodiscover_modules

    from radiofeed.scheduler import scheduler

    autodiscover_modules("jobs")

    scheduler.start()


if __name__ == "__main__":
    main()

#!/usr/bin/env python
import os

from cookiecutter.main import cookiecutter


def main() -> None:
    """Django management entry point."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "radiofeed.settings")
    try:
        from django.core.management.utils import get_random_secret_key
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    cookiecutter(
        "ansible-dokku-tmpl", extra_context={"secret_key": get_random_secret_key()}
    )


if __name__ == "__main__":
    main()

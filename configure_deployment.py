#!/usr/bin/env python


import os
import pathlib
from argparse import ArgumentParser

from cookiecutter.main import cookiecutter

parser = ArgumentParser(
    prog="configure_deployment",
    description="Configure deployment",
)
parser.add_argument(
    "cookiecutter",
    help="Path to cookiecutter template",
)

parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Overwrite existing ansible configuration, if exists",
)


def main() -> None:
    """Deployment command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "radiofeed.settings")
    try:
        from django.conf import settings
        from django.contrib.auth.management import get_system_username
        from django.core.management.utils import get_random_secret_key

    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    args = parser.parse_args()
    cookiecutter(
        str(pathlib.Path(settings.BASE_DIR / "cookiecutters")),
        directory=args.cookiecutter,
        overwrite_if_exists=args.overwrite,
        extra_context={
            "secret_key": get_random_secret_key(),
            "username": get_system_username(),
        },
    )


if __name__ == "__main__":
    main()

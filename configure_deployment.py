#!/usr/bin/env python


import os
import pathlib
import shutil
import sys
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

    cookiecutter_dir = pathlib.Path(settings.BASE_DIR / "cookiecutters")

    dest_dir = settings.BASE_DIR / "deployments"
    dest_dir.mkdir(exist_ok=True)

    target_dir = dest_dir / args.cookiecutter

    if target_dir.exists() and not args.overwrite:
        sys.stderr.write(f"{target_dir} already exists\n")
        sys.exit(1)

    cookiecutter(
        str(cookiecutter_dir),
        directory=args.cookiecutter,
        overwrite_if_exists=True,
        extra_context={
            "secret_key": get_random_secret_key(),
            "username": get_system_username(),
        },
    )

    new_dir = settings.BASE_DIR / args.cookiecutter

    if args.overwrite:
        shutil.rmtree(target_dir)

    new_dir.replace(target_dir)


if __name__ == "__main__":
    main()

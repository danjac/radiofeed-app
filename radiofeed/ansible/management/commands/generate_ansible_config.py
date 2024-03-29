import pathlib
from argparse import ArgumentParser

from cookiecutter.main import cookiecutter
from django.conf import settings
from django.contrib.auth.management import get_system_username
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    """Generate ansible from cookiecutter template."""

    help = """Generate ansible from cookiecutter template."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "cookiecutter",
            help="Path to cookiecutter template",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing ansible configuration, if exists",
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""

        cookiecutter(
            str(pathlib.Path(settings.BASE_DIR / "cookiecutters")),
            directory=options["cookiecutter"],
            overwrite_if_exists=options["overwrite"],
            extra_context={
                "secret_key": get_random_secret_key(),
                "username": get_system_username(),
            },
        )

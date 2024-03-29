import pathlib
from argparse import ArgumentParser

from cookiecutter.main import cookiecutter
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    """Generate ansible from cookiecutter template."""

    help = """Generate ansible from cookiecutter template."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "cookiecutter",
            help="Name of cookiecutter.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing ansible configuration, if exists",
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""

        cookiecutter_path = pathlib.Path(
            settings.BASE_DIR
            / "radiofeed"
            / "ansible"
            / "cookiecutters"
            / options["cookiecutter"]
        )

        cookiecutter(
            str(cookiecutter_path),
            overwrite_if_exists=options["overwrite"],
            extra_context={
                "secret_key": get_random_secret_key(),
            },
        )

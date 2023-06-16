#!/usr/bin/env python

"Django's command-line utility for administrative tasks."


import os
import sys
from typing import Final

_IMPORT_ERR_MSG: Final = (
    "Couldn't import Django. Are you sure it's installed and "
    "available on your PYTHONPATH environment variable? Did you "
    "forget to activate a virtual environment?"
)


def main() -> None:
    """Django management entry point."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "radiofeed.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(_IMPORT_ERR_MSG) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

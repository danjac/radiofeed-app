from django.core.exceptions import ValidationError

from radiofeed.feedparser.validators import _url_validator


def explicit(value):
    if value and value.casefold() in ("clean", "yes"):
        return True
    return False


def url_or_none(value):
    try:
        _url_validator(value)
        return value
    except ValidationError:
        return None


def duration(value):
    if not value:
        return ""

    try:
        # plain seconds value
        return str(int(value))
    except ValueError:
        pass

    try:
        return ":".join(
            [
                str(v)
                for v in [int(v) for v in value.split(":")[:3]]
                if v in range(0, 60)
            ]
        )
    except ValueError:
        return ""

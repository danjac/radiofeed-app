from radiofeed.common.template import normalize_url


def language(value):
    """Returns two-character language code.

    Args:
        value (str)

    Returns:
        str
    """
    return value[:2].casefold()


def explicit(value):
    """Checks if podcast or episode explicit.

    Args:
        value (str | None)

    Returns:
        bool
    """
    return bool(value and value.casefold() in ("clean", "yes"))


def url(value):
    """Returns a URL value. Will try to prefix with https:// if only domain provided.

    If cannot resolve as a valid URL will return None.

    Args:
        value (str | None)

    Returns:
        str | None
    """
    return normalize_url(value) or None


def duration(value):
    """Given a duration value will ensure all values fall within range.

    Examples:
        - 3600 (plain int) -> "3600"
        - 3:60:50:1000 -> "3:60:50"

    Return empty string if cannot resolve.

    Args:
        value (str | None)

    Returns:
        str
    """
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

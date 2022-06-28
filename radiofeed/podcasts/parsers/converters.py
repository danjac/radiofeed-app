def complete(value):
    if value and value.casefold() == "yes":
        return True
    return False


def explicit(value):
    if value and value.casefold() in ("clean", "yes"):
        return True
    return False


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


def language_code(value):
    return (value or "en")[:2]

from __future__ import annotations


def complete(value: str) -> bool:
    return bool(value and value.casefold() == "yes")


def explicit(value: str) -> bool:
    return bool(value and value.casefold() in ("clean", "yes"))


def duration(value: str) -> str:
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


def language_code(value: str) -> str:
    return (value or "en")[:2]


def int_or_none(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

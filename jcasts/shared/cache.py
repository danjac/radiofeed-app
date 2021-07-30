import uuid

from functools import lru_cache


@lru_cache
def make_key_prefix(key_prefix: str, version: int) -> str:
    # prefix a uuid value to bust cache on restarts
    return ":".join(
        [value for value in (key_prefix, str(version), uuid.uuid4().hex) if value]
    )


def make_cache_key(key: str, key_prefix: str, version: int) -> str:
    return ":".join([make_key_prefix(key_prefix, version), key])

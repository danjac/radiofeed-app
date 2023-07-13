from collections.abc import Callable, Generator

import pytest
from django.conf import Settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


@pytest.fixture(autouse=True)
def _settings_overrides(settings: Settings) -> None:
    """Default settings for all tests."""
    settings.ALLOWED_HOSTS = ["example.com", "testserver", "localhost"]
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
    settings.CACHEOPS_ENABLED = False
    settings.LOGGING = None
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture()
def _locmem_cache(settings: Settings) -> Generator:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture(scope="session")
def get_response() -> Callable[[HttpRequest], HttpResponse]:
    return lambda req: HttpResponse()

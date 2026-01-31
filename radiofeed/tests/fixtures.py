from typing import TYPE_CHECKING

import pytest
from django.contrib.auth.signals import user_logged_in
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from django.conf import Settings


@pytest.fixture
def site():
    return Site.objects.get_current()


@pytest.fixture(autouse=True)
def _settings_overrides(settings: Settings) -> None:
    """Default settings for all tests."""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
    settings.ALLOWED_HOSTS = ["example.com", "testserver", "localhost"]
    settings.LOGGING = None
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def _locmem_cache(settings: Settings) -> Generator:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture(scope="session", autouse=True)
def _disable_update_last_login() -> None:
    """
    Disable the update_last_login signal receiver to reduce login overhead.

    See: https://adamj.eu/tech/2024/09/18/django-test-speed-last-login/
    """
    user_logged_in.disconnect(dispatch_uid="update_last_login")


@pytest.fixture(scope="session")
def get_response() -> Callable[[HttpRequest], HttpResponse]:
    return lambda req: HttpResponse()

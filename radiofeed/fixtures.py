import pytest
from django.core.cache import cache
from django.http import HttpResponse


@pytest.fixture(autouse=True)
def settings_overrides(settings):
    """Default settings for all tests."""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
    settings.LOGGING = None
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def locmem_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture(scope="session")
def get_response():
    return lambda req: HttpResponse()

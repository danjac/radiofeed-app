import pytest
from django.contrib.auth.signals import user_logged_in
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.http import HttpResponse


@pytest.fixture
def site():
    return Site.objects.get_current()


@pytest.fixture(autouse=True)
def _settings_overrides(settings) -> None:
    """Default settings for all tests."""
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
    settings.TASKS = {
        "default": {"BACKEND": "django.tasks.backends.dummy.DummyBackend"}
    }
    settings.ALLOWED_HOSTS = ["example.com", "testserver", "localhost"]
    settings.LOGGING = None
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def _locmem_cache(settings):
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
    yield
    cache.clear()


@pytest.fixture
def _immediate_task_backend(settings):
    settings.TASKS = {
        "default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}
    }


@pytest.fixture(scope="session", autouse=True)
def _disable_update_last_login():
    """
    Disable the update_last_login signal receiver to reduce login overhead.

    See: https://adamj.eu/tech/2024/09/18/django-test-speed-last-login/
    """
    user_logged_in.disconnect(dispatch_uid="update_last_login")


@pytest.fixture(scope="session")
def get_response():
    return lambda req: HttpResponse()

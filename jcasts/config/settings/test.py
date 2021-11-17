import django_rq.queues
import fakeredis

from split_settings.tools import include

from jcasts.config.settings.base import ALLOWED_HOSTS

include("base.py")

LOGGING = None

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

ALLOWED_HOSTS += [".example.com"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}

# workaround: https://github.com/rq/django-rq/issues/317#issuecomment-505266162

django_rq.queues.get_redis_connection = (
    lambda _, strict: fakeredis.FakeStrictRedis() if strict else fakeredis.FakeRedis()
)

RQ_QUEUES = {
    "default": {
        "ASYNC": False,
    },
    "feeds": {
        "ASYNC": False,
    },
    "mail": {
        "ASYNC": False,
    },
}

PODCASTINDEX_API_KEY = "notset"  # nosec
PODCASTINDEX_API_SECRET = "notset"  # nosec

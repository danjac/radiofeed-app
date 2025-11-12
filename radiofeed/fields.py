import functools

from django.db import models

from radiofeed.validators import http_url_validator

# URLField with sensible defaults
URLField = functools.partial(
    models.URLField,
    max_length=2083,
    validators=[http_url_validator],
)

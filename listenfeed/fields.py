import functools

from django.db import models

from listenfeed.validators import url_validator

# URLField with sensible defaults
URLField = functools.partial(
    models.URLField,
    max_length=2083,
    validators=[url_validator],
)

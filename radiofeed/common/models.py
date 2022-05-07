from __future__ import annotations

from django.core.validators import validate_slug
from django.db import models
from django_countries.fields import CountryField
from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    # metadata
    site_name: str = models.CharField(max_length=255, default="Radiofeed")
    description: str = models.TextField(blank=True)
    keywords: str = models.TextField(blank=True)

    # site owner
    site_owner: str = models.CharField(max_length=255, blank=True)
    contact_email: str = models.EmailField(default="admin@localhost")
    twitter_handle: str = models.CharField(
        max_length=100, blank=True, validators=[validate_slug]
    )

    # legal stuff
    host_country: str = CountryField(default="FI")
    age_of_consent: int = models.PositiveSmallIntegerField(default=18)

    def __str__(self):
        return self.site_name

    class Meta:
        verbose_name = "Site Configuration"

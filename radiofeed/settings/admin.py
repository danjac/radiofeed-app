from __future__ import annotations

from django.contrib import admin
from solo.admin import SingletonModelAdmin

from radiofeed.settings.models import SiteConfiguration

admin.site.register(SiteConfiguration, SingletonModelAdmin)

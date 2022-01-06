from __future__ import annotations

from django.contrib import admin
from django.contrib.sites.models import Site
from django.http import HttpRequest


class AdminSite(admin.AdminSite):
    def each_context(self, request: HttpRequest) -> dict:

        site = Site.objects.get_current()

        return super().each_context(request) | {
            "site_header": f"{site.name} Administration",
        }

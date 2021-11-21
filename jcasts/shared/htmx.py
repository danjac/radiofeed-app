from __future__ import annotations

import enum
import functools
import json

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, HttpResponseForbidden


class HxTrigger(enum.Enum):
    HX_TRIGGER = "HX-Trigger"
    HX_TRIGGER_AFTER_SETTLE = "HX-Trigger-After-Settle"
    HX_TRIGGER_AFTER_SWAP = "HX-Trigger-After-Swap"


def hx_redirect_to_login(
    path: str = settings.LOGIN_REDIRECT_URL,
    redirect_field_name: str = REDIRECT_FIELD_NAME,
) -> HttpResponse:
    response = HttpResponseForbidden()
    response["HX-Redirect"] = redirect_to_login(
        path, redirect_field_name=REDIRECT_FIELD_NAME
    ).url
    response["HX-Refresh"] = "true"
    return response


def with_hx_trigger(
    response: HttpResponse,
    data: str | dict | None,
    header: HxTrigger = HxTrigger.HX_TRIGGER,
) -> HttpResponse:
    """Returns HX-Trigger header. If header already
    added to response, will add the new trigger
    to the existing header.

    See:

    https://htmx.org/headers/hx-trigger/
    """

    if not data:
        return response

    if trigger := response.headers.get(header.value, None):
        try:
            payload = json.loads(trigger)
        except json.JSONDecodeError:
            # probably plain string
            payload = {trigger: ""}
    else:
        payload = {}

    if isinstance(data, str):
        data = {data: ""}

    response[header.value] = json.dumps({**payload, **data})
    return response


with_hx_trigger_after_swap = functools.partial(
    with_hx_trigger, header=HxTrigger.HX_TRIGGER_AFTER_SWAP
)

with_hx_trigger_after_settle = functools.partial(
    with_hx_trigger, header=HxTrigger.HX_TRIGGER_AFTER_SETTLE
)

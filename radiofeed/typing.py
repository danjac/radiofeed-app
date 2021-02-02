from typing import Callable, Union

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

AnyUser = Union[AnonymousUser, settings.AUTH_USER_MODEL]

HttpCallable = Callable[[HttpRequest], HttpResponse]

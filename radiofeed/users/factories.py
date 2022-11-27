from __future__ import annotations

import functools

from allauth.account.models import EmailAddress

from radiofeed.common.factories import (
    NotSet,
    email_notset,
    notset,
    password_notset,
    username_notset,
)
from radiofeed.users.models import User


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=username_notset(username),
        email=email_notset(email),
        password=password_notset(password),
        **kwargs,
    )


user_notset = functools.partial(notset, default_value=create_user)


def create_email_address(
    *,
    user: User = NotSet,
    email: str = NotSet,
    verified: bool = True,
    primary: bool = False,
) -> EmailAddress:
    return EmailAddress.objects.create(
        user=user_notset(user),
        email=email_notset(email),
        verified=verified,
        primary=primary,
    )

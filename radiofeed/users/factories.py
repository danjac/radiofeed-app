from __future__ import annotations

import functools

from allauth.account.models import EmailAddress

from radiofeed.common.factories import (
    NotSet,
    default_email,
    default_password,
    default_username,
    set_default,
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
        username=default_username(username),
        email=default_email(email),
        password=default_password(password),
        **kwargs,
    )


default_user = functools.partial(set_default, default_value=create_user)


def create_email_address(
    *,
    user: User = NotSet,
    email: str = NotSet,
    verified: bool = True,
    primary: bool = False,
) -> EmailAddress:
    return EmailAddress.objects.create(
        user=default_user(user),
        email=default_email(email),
        verified=verified,
        primary=primary,
    )

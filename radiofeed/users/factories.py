from __future__ import annotations

from allauth.account.models import EmailAddress

from radiofeed.common.factories import (
    NotSet,
    notset,
    notset_email,
    notset_password,
    notset_username,
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
        username=notset_username(username),
        email=notset_email(email),
        password=notset_password(password),
        **kwargs,
    )


def create_email_address(
    *,
    user: User = NotSet,
    email: str = NotSet,
    verified: bool = True,
    primary: bool = False,
) -> EmailAddress:
    return EmailAddress.objects.create(
        user=notset(user, create_user),
        email=notset_email(email),
        verified=verified,
        primary=primary,
    )

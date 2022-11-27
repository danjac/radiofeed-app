from __future__ import annotations

import faker

from allauth.account.models import EmailAddress

from radiofeed.common.factories import NotSet, notset
from radiofeed.users.models import User

_faker = faker.Faker()


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=notset(username, _faker.unique.user_name),
        email=notset(email, _faker.unique.email),
        password=notset(password, _faker.password),
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
        email=notset(email, _faker.unique.email),
        verified=verified,
        primary=primary,
    )

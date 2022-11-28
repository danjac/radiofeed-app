from __future__ import annotations

import functools
import itertools

from allauth.account.models import EmailAddress

from radiofeed.common.factories import NotSet, set_default
from radiofeed.users.models import User

_username_seq = (f"user-{n}" for n in itertools.count())
_email_seq = (f"user-{n}@example.com" for n in itertools.count())


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=set_default(username, next(_username_seq)),
        email=set_default(email, next(_email_seq)),
        password=set_default(password, "testpass1"),
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
        email=set_default(email, next(_email_seq)),
        verified=verified,
        primary=primary,
    )

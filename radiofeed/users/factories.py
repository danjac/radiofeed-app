from __future__ import annotations

import functools
import itertools

from allauth.account.models import EmailAddress

from radiofeed.common.factories import NotSet, set_default
from radiofeed.users.models import User

_username_seq = (f"user-{n}" for n in itertools.count())
_email_seq = (f"user-{n}@example.com" for n in itertools.count())

default_username = functools.partial(
    set_default, default_value=lambda: next(_username_seq)
)

default_email = functools.partial(set_default, default_value=lambda: next(_email_seq))


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
        email=default_email(email),
        verified=verified,
        primary=primary,
    )

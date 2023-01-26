from __future__ import annotations

from allauth.account.models import EmailAddress

from radiofeed.factories import NotSet, counter, resolve
from radiofeed.users.models import User

_username_seq = counter("user-{n}")
_email_seq = counter("user-{n}@example.com")


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=resolve(username, lambda: next(_username_seq)),
        email=resolve(email, lambda: next(_email_seq)),
        password=resolve(password, "testpass1"),
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
        user=resolve(user, create_user),
        email=resolve(email, lambda: next(_email_seq)),
        verified=verified,
        primary=primary,
    )

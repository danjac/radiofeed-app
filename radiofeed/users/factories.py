from __future__ import annotations

from allauth.account.models import EmailAddress

from radiofeed.factories import NotSet, Sequence, resolve
from radiofeed.users.models import User

_usernames = Sequence("user-{n}")
_emails = Sequence("user-{n}@example.com")


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=resolve(username, _usernames),
        email=resolve(email, _emails),
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
        email=resolve(email, _emails),
        verified=verified,
        primary=primary,
    )

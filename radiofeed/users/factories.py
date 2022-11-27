from __future__ import annotations

from allauth.account.models import EmailAddress
from faker import Faker

from radiofeed.users.models import User

faker = Faker()


def create_user(
    *, username: str = "", email: str = "", password="testpass1", **kwargs
) -> User:
    return User.objects.create_user(
        username=username or faker.unique.user_name(),
        email=email or faker.unique.email(),
        password=password,
        **kwargs,
    )


def create_email_address(
    *,
    user: User | None = None,
    email: str = "",
    verified: bool = True,
    primary: bool = False,
) -> EmailAddress:
    return EmailAddress.objects.create(
        user=user or create_user(),
        email=email or faker.unique.email(),
        verified=verified,
        primary=primary,
    )

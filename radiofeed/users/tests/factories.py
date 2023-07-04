from allauth.account.models import EmailAddress
from faker import Faker

from radiofeed.tests.factories import NotSet, resolve
from radiofeed.users.models import User

_faker = Faker()


def create_user(
    *,
    username: str = NotSet,
    email: str = NotSet,
    password: str = NotSet,
    **kwargs,
) -> User:
    return User.objects.create_user(
        username=resolve(username, _faker.unique.user_name),
        email=resolve(email, _faker.unique.email),
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
        email=resolve(email, _faker.unique.email),
        verified=verified,
        primary=primary,
    )

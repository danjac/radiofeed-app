from allauth.account.models import EmailAddress
from factory import django
from factory.declarations import LazyAttribute, Sequence, SubFactory

from radiofeed.users.models import User


class UserFactory(django.DjangoModelFactory):
    username = Sequence(lambda n: f"user-{n}")
    email = Sequence(lambda n: f"user-{n}@example.com")
    password = django.Password("testpass")

    class Meta:
        model = User


class EmailAddressFactory(django.DjangoModelFactory):
    user = SubFactory(UserFactory)
    email = LazyAttribute(lambda a: a.user.email)
    verified = True

    class Meta:
        model = EmailAddress

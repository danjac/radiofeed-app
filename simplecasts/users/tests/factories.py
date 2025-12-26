import factory
from allauth.account.models import EmailAddress

from simplecasts.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.django.Password("testpass")

    class Meta:
        model = User


class EmailAddressFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    email = factory.LazyAttribute(lambda a: a.user.email)
    verified = True

    class Meta:
        model = EmailAddress

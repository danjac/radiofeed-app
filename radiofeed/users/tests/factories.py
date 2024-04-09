import factory
from faker import Faker

from radiofeed.users.models import User

_faker = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.django.Password("testpass")

    class Meta:
        model = User

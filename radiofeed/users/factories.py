from __future__ import annotations

from factory import Faker, post_generation
from factory.django import DjangoModelFactory

from radiofeed.users.models import User


class UserFactory(DjangoModelFactory):

    username: str = Faker("user_name")
    email: str = Faker("email")

    @post_generation
    def password(self, *args, **kwargs):
        self.set_password("testpass1")

    class Meta:
        model = User
        django_get_or_create = ["username"]

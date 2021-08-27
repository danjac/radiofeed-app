from django.contrib.auth import get_user_model
from factory import Faker, post_generation
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    username: str = Faker("user_name")
    email: str = Faker("email")

    @post_generation
    def password(self, *args, **kwargs):
        self.set_password("testpass1")

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]

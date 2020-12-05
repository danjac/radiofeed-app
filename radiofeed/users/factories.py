# Django
from django.contrib.auth import get_user_model

# Third Party Libraries
from factory import Faker, post_generation
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self, *args, **kwargs):
        self.set_password("testpass1")

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]

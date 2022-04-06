from factory import Faker, post_generation
from factory.django import DjangoModelFactory

from jcasts.users.models import User

DEFAULT_PASSWORD = "testpass1"  # nosec


class UserFactory(DjangoModelFactory):

    username: str = Faker("user_name")
    email: str = Faker("email")

    @post_generation
    def password(self, *args, **kwargs):
        self.set_password(DEFAULT_PASSWORD)

    class Meta:
        model = User
        django_get_or_create = ["username"]

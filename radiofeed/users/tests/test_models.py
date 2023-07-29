import pytest

from radiofeed.users.models import User


class TestUserManager:
    email = "tester@gmail.com"

    @pytest.mark.django_db()
    def test_create_user(self):
        password = User.objects.make_random_password()

        user = User.objects.create_user(
            username="tester1", email=self.email, password=password
        )
        assert user.check_password(password)

    @pytest.mark.django_db()
    def test_create_superuser(self):
        password = User.objects.make_random_password()

        user = User.objects.create_superuser(
            username="tester2", email=self.email, password=password
        )
        assert user.is_superuser
        assert user.is_staff

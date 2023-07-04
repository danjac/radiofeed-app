import pytest
from allauth.account.models import EmailAddress

from radiofeed.users.models import User
from radiofeed.users.tests.factories import create_user


class TestUserManager:
    email = "tester@gmail.com"

    @pytest.mark.parametrize(
        ("active", "send_email_notifications", "exists"),
        [
            (True, True, True),
            (True, False, False),
            (False, True, False),
        ],
    )
    @pytest.mark.django_db()
    def test_email_notification_recipients(
        self, active, send_email_notifications, exists
    ):
        create_user(is_active=active, send_email_notifications=send_email_notifications)
        assert User.objects.email_notification_recipients().exists() == exists

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

    @pytest.mark.django_db()
    def test_for_email_matching_email_field(self):
        user = create_user(email=self.email)
        assert User.objects.for_email(self.email).first() == user

    @pytest.mark.django_db()
    def test_for_email_matching_email_address_instance(self, user):
        EmailAddress.objects.create(user=user, email=self.email)
        assert User.objects.for_email(self.email).first() == user


class TestUserModel:
    @pytest.mark.django_db()
    def test_get_email_addresses(self, user):
        email = "test1@gmail.com"
        user.emailaddress_set.create(email=email)
        emails = user.get_email_addresses()
        assert user.email in emails
        assert email in emails

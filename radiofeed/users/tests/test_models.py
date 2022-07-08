from __future__ import annotations

import pytest

from allauth.account.models import EmailAddress

from radiofeed.users.factories import UserFactory
from radiofeed.users.models import User


class TestUserManager:
    email = "tester@gmail.com"

    @pytest.mark.parametrize(
        "active,send_email_notifications,exists",
        [
            (True, True, True),
            (True, False, False),
            (False, True, False),
        ],
    )
    def test_email_notification_recipients(
        self, db, active, send_email_notifications, exists
    ):
        UserFactory(is_active=active, send_email_notifications=send_email_notifications)
        assert User.objects.email_notification_recipients().exists() == exists

    def test_create_user(self, db):

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            username="tester1", email=self.email, password=password
        )
        assert user.check_password(password)

    def test_create_superuser(self, db):

        password = User.objects.make_random_password()

        user = User.objects.create_superuser(
            username="tester2", email=self.email, password=password
        )
        assert user.is_superuser
        assert user.is_staff

    def test_for_email_matching_email_field(self, db):

        user = UserFactory(email=self.email)
        assert User.objects.for_email(self.email).first() == user

    def test_for_email_matching_email_address_instance(self, user):

        EmailAddress.objects.create(user=user, email=self.email)
        assert User.objects.for_email(self.email).first() == user


class TestUserModel:
    def test_get_email_addresses(self, user):
        email = "test1@gmail.com"
        user.emailaddress_set.create(email=email)
        emails = user.get_email_addresses()
        assert user.email in emails
        assert email in emails

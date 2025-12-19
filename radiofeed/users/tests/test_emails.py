import pytest

from radiofeed.users.emails import get_recipients
from radiofeed.users.tests.factories import EmailAddressFactory


class TestGetRecipients:
    @pytest.mark.django_db
    def test_ok(self):
        EmailAddressFactory(
            verified=True,
            primary=True,
        )
        assert get_recipients().exists() is True

    @pytest.mark.django_db
    def test_email_not_verified(self):
        EmailAddressFactory(
            verified=False,
            primary=True,
        )

        assert get_recipients().exists() is False

    @pytest.mark.django_db
    def test_email_not_primary(self):
        EmailAddressFactory(
            verified=True,
            primary=False,
        )

        assert get_recipients().exists() is False

    @pytest.mark.django_db
    def test_user_inactive(self):
        EmailAddressFactory(
            user__is_active=False,
            verified=True,
            primary=True,
        )

        assert get_recipients().exists() is False

    @pytest.mark.django_db
    def test_user_disabled_emails(self):
        EmailAddressFactory(
            user__send_email_notifications=False,
            verified=True,
            primary=True,
        )

        assert get_recipients().exists() is False

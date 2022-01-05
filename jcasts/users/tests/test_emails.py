import pytest

from jcasts.users.emails import get_inline_css, send_user_notification_email
from jcasts.users.factories import UserFactory


class TestSendUserNotificationEmail:
    def test_enabled(self, user, mailoutbox):
        send_user_notification_email(
            user,
            "testing!",
            "account/emails/test_email.txt",
            "account/emails/test_email.html",
        )

        assert len(mailoutbox) == 1

    def test_disabled(self, db, mailoutbox):
        user = UserFactory(send_email_notifications=False)
        send_user_notification_email(
            user,
            "testing!",
            "account/emails/test_email.txt",
            "account/emails/test_email.html",
        )

        assert len(mailoutbox) == 0


class TestGetInlineCss:
    @pytest.fixture
    def clear_lru_cache(self):
        get_inline_css.cache_clear()
        yield

    def test_ok(self, clear_lru_cache):
        assert get_inline_css()

    def test_error(self, mocker, clear_lru_cache):
        mocker.patch("builtins.open", side_effect=IOError)
        assert not get_inline_css()

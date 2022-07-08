from __future__ import annotations

from radiofeed.users.emails import send_user_notification_email


class TestSendUserNotificationEmail:
    def test_send(self, user, mailoutbox):
        send_user_notification_email(
            user,
            "testing!",
            "account/emails/test_email.txt",
            "account/emails/test_email.html",
        )

        assert len(mailoutbox) == 1

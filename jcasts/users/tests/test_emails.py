from jcasts.users.emails import send_user_notification_email
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

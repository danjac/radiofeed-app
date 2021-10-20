from django.core.mail import EmailMessage

from jcasts.lib.email import RqBackend


class TestRqBackend:
    def test_send_messages(self, settings, mailoutbox):
        settings.RQ_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        msg = EmailMessage(
            subject="test",
            to=["tester@gmail.com"],
            body="Hi",
        )
        assert RqBackend().send_messages([msg]) == 1
        assert len(mailoutbox) == 1

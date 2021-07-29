from django.core.mail import EmailMessage

from jcasts.shared.email import RqBackend


class TestRqBackend:
    def test_send_messages(self):
        msg = EmailMessage(
            subject="test",
            to=["tester@gmail.com"],
            body="Hi",
        )
        assert RqBackend().send_messages([msg]) == 1

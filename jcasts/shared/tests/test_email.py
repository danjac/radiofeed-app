import pytest

from django.core.mail import EmailMessage

from jcasts.shared.email import RqBackend, send_rq_message


@pytest.fixture
def message():

    return EmailMessage(
        subject="test",
        to=["tester@gmail.com"],
        body="Hi",
    )


class TestRqBackend:
    def test_send_messages(self, settings, mocker):
        mock_send_msg = mocker.patch("jcasts.shared.email.send_rq_message.delay")
        settings.RQ_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        assert RqBackend().send_messages([message]) == 1
        mock_send_msg.assert_called_with(message)


class TestSendRqMessage:
    def test_send(self, mocker, message):
        mocker.patch("jcasts.shared.email.get_connection")
        send_rq_message(message)
        assert message.connection

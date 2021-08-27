from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django_rq import job


class RqBackend(BaseEmailBackend):
    def send_messages(self, email_messages):

        for message in email_messages:
            send_rq_message.delay(message)

        return len(email_messages)


@job(settings.RQ_EMAIL_QUEUE)
def send_rq_message(message):
    message.connection = get_connection(settings.RQ_EMAIL_BACKEND, fail_silently=False)
    message.send(fail_silently=False)

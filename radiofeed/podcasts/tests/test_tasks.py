from radiofeed.podcasts.tasks import send_recommendations_email


class TestTasks:
    def test_recommendations_email(self, mocker, user):
        patched = mocker.patch("radiofeed.podcasts.emails.send_recommendations_email")
        send_recommendations_email(user.id)
        patched.assert_called_with(user)

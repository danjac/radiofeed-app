from jcasts.users.forms import RecaptchSignupForm


class TestRecaptchaSignupForm:
    def test_has_recaptcha(self, db, settings):
        settings.RECAPTCHA_PUBLIC_KEY = "test"
        settings.RECAPTCHA_PRIVATE_KEY = "test"

        form = RecaptchSignupForm()
        assert form["captcha"]

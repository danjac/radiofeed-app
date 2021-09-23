from jcasts.users.forms import RecaptchaSignupForm


class TestRecaptchaSignupForm:
    def test_has_recaptcha(self, db, settings):
        settings.RECAPTCHA_PUBLIC_KEY = "test"
        settings.RECAPTCHA_PRIVATE_KEY = "test"

        form = RecaptchaSignupForm()
        assert form["captcha"]

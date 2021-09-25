from jcasts.users.forms import RecaptchaSignupForm


class TestRecaptchaSignupForm:
    def test_has_recaptcha(self, settings):
        settings.RECAPTCHA_PUBLIC_KEY = "test"
        settings.RECAPTCHA_PRIVATE_KEY = "test"

        form = RecaptchaSignupForm()
        assert form["captcha"]

    def test_signup(self, rf, django_user_model):
        RecaptchaSignupForm().signup(rf.get("/"), django_user_model())

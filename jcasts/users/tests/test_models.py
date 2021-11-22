from allauth.account.models import EmailAddress

from jcasts.users.factories import UserFactory


class TestUserManager:
    email = "tester@gmail.com"

    def test_create_user(self, db, django_user_model):

        password = django_user_model.objects.make_random_password()

        user = django_user_model.objects.create_user(
            username="tester1", email=self.email, password=password
        )
        assert user.check_password(password)

    def test_create_superuser(self, db, django_user_model):

        password = django_user_model.objects.make_random_password()

        user = django_user_model.objects.create_superuser(
            username="tester2", email=self.email, password=password
        )
        assert user.is_superuser
        assert user.is_staff

    def test_for_email_matching_email_field(self, db, django_user_model):

        user = UserFactory(email=self.email)
        assert django_user_model.objects.for_email(self.email).first() == user

    def test_for_email_matching_email_address_instance(self, user, django_user_model):

        EmailAddress.objects.create(user=user, email=self.email)
        assert django_user_model.objects.for_email(self.email).first() == user


class TestUserModel:
    def test_get_email_addresses(self, user):
        email = "test1@gmail.com"
        user.emailaddress_set.create(email=email)
        emails = user.get_email_addresses()
        assert user.email in emails
        assert email in emails

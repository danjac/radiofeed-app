import pytest

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

    def test_matches_usernames(self, db, django_user_model):
        user_1 = UserFactory(username="first")
        user_2 = UserFactory(username="second")
        user_3 = UserFactory(username="third")

        names = ["second", "FIRST", "SEconD"]  # duplicate

        users = django_user_model.objects.matches_usernames(names)

        assert len(users) == 2
        assert user_1 in users
        assert user_2 in users
        assert user_3 not in users

        # check empty set returns no results
        assert django_user_model.objects.matches_usernames([]).count() == 0


class TestUserModel:
    def test_get_email_addresses(self, user):
        email = "test1@gmail.com"
        user.emailaddress_set.create(email=email)
        emails = user.get_email_addresses()
        assert user.email in emails
        assert email in emails

    @pytest.mark.parametrize(
        "expected,params",
        [
            (
                "https://www.gravatar.com/avatar/5658ffccee7f0ebfda2b226238b1eb6e?s=30&d=retro&r=g",
                {},
            ),
            (
                "https://www.gravatar.com/avatar/5658ffccee7f0ebfda2b226238b1eb6e?s=100&d=retro&r=g",
                {"size": 100},
            ),
        ],
    )
    def test_get_gravatar_url(self, django_user_model, expected, params):
        user = django_user_model(email="email@example.com")
        assert user.get_gravatar_url(**params) == expected

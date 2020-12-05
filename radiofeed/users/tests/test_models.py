# Third Party Libraries
import pytest
from allauth.account.models import EmailAddress

# Local
from ..factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_create_user(self, user_model):

        user = user_model.objects.create_user(
            username="tester", email="tester@gmail.com", password="t3ZtP4s31"
        )
        assert user.check_password("t3ZtP4s31")

    def test_create_superuser(self, user_model):

        user = user_model.objects.create_superuser(
            username="tester", email="tester@gmail.com", password="t3ZtP4s31"
        )
        assert user.is_superuser
        assert user.is_staff

    def test_for_email_matching_email_field(self, user_model):

        user = UserFactory(email="test@gmail.com")
        assert user_model.objects.for_email("test@gmail.com").first() == user

    def test_for_email_matching_email_address_instance(self, user_model):

        user = UserFactory()
        EmailAddress.objects.create(user=user, email="test@gmail.com")
        assert user_model.objects.for_email("test@gmail.com").first() == user

    def test_matches_usernames(self, user_model):
        user_1 = UserFactory(username="first")
        user_2 = UserFactory(username="second")
        user_3 = UserFactory(username="third")

        names = ["second", "FIRST", "SEconD"]  # duplicate

        users = user_model.objects.matches_usernames(names)
        assert len(users) == 2
        assert user_1 in users
        assert user_2 in users
        assert user_3 not in users

        # check empty set returns no results
        assert user_model.objects.matches_usernames([]).count() == 0


class TestUserModel:
    def test_get_email_addresses(self, user):

        user.emailaddress_set.create(email="test1@gmail.com")
        emails = user.get_email_addresses()
        assert user.email in emails
        assert "test1@gmail.com" in emails

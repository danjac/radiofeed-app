from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..factories import UserFactory

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user(self):

        user = User.objects.create_user(
            username="tester", email="tester@gmail.com", password="t3ZtP4s31"
        )
        self.assertTrue(user.check_password("t3ZtP4s31"))

    def test_create_superuser(self):

        user = User.objects.create_superuser(
            username="tester", email="tester@gmail.com", password="t3ZtP4s31"
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_for_email_matching_email_field(self):

        user = UserFactory(email="test@gmail.com")
        self.assertEqual(User.objects.for_email("test@gmail.com").first(), user)

    def test_for_email_matching_email_address_instance(self):

        user = UserFactory()
        EmailAddress.objects.create(user=user, email="test@gmail.com")
        self.assertEqual(User.objects.for_email("test@gmail.com").first(), user)

    def test_matches_usernames(self):
        user_1 = UserFactory(username="first")
        user_2 = UserFactory(username="second")
        user_3 = UserFactory(username="third")

        names = ["second", "FIRST", "SEconD"]  # duplicate

        users = User.objects.matches_usernames(names)
        self.assertEqual(len(users), 2)
        self.assertTrue(user_1 in users)
        self.assertTrue(user_2 in users)
        self.assertFalse(user_3 in users)

        # check empty set returns no results
        self.assertEqual(User.objects.matches_usernames([]).count(), 0)


class UserModelTests(TestCase):
    def test_get_email_addresses(self):
        user = UserFactory()
        user.emailaddress_set.create(email="test1@gmail.com")
        emails = user.get_email_addresses()
        self.assertTrue(user.email in emails)
        self.assertTrue("test1@gmail.com" in emails)

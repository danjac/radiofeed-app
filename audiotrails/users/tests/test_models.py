from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..factories import UserFactory

User = get_user_model()


class UserManagerTests(TestCase):
    email = "tester@gmail.com"

    def test_create_user(self) -> None:

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            username="tester1", email=self.email, password=password
        )
        self.assertTrue(user.check_password(password))

    def test_create_superuser(self) -> None:

        password = User.objects.make_random_password()

        user = User.objects.create_superuser(
            username="tester2", email=self.email, password=password
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_for_email_matching_email_field(self) -> None:

        user = UserFactory(email=self.email)
        self.assertEqual(User.objects.for_email(self.email).first(), user)

    def test_for_email_matching_email_address_instance(self) -> None:

        user = UserFactory()
        EmailAddress.objects.create(user=user, email=self.email)
        self.assertEqual(User.objects.for_email(self.email).first(), user)

    def test_matches_usernames(self) -> None:
        user_1 = UserFactory(username="first")
        user_2 = UserFactory(username="second")
        user_3 = UserFactory(username="third")

        names = ["second", "FIRST", "SEconD"]  # duplicate

        users = User.objects.matches_usernames(names)
        self.assertEqual(len(users), 2)
        self.assertIn(user_1, users)
        self.assertIn(user_2, users)
        self.assertNotIn(user_3, users)

        # check empty set returns no results
        self.assertEqual(User.objects.matches_usernames([]).count(), 0)


class UserModelTests(TestCase):
    def test_get_email_addresses(self) -> None:
        user = UserFactory()
        email = "test1@gmail.com"
        user.emailaddress_set.create(email=email)
        emails = user.get_email_addresses()
        self.assertIn(user.email, emails)
        self.assertIn(email, emails)

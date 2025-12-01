from listenwave.users.models import User


class TestUserModel:
    def test_name_has_first_and_last_name(self):
        """Test name property with first and last name."""
        user = User(first_name="John", username="johndoe")
        assert user.name == "John"

    def test_name_has_only_username(self):
        """Test name property with only username."""
        user = User(username="johndoe")
        assert user.name == "johndoe"

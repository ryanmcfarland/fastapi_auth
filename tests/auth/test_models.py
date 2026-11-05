import pytest
from pydantic import ValidationError

from app.auth.models import RegisterUser


@pytest.fixture
def register_user_model():
    """Fixture to provide the RegisterUser model class."""

    return RegisterUser


class TestRegisterUserValidation:
    """Test suite for RegisterUser model validation."""

    def test_valid_user_with_all_fields(self, register_user_model):
        """Test creating a valid user with all fields provided."""
        user = register_user_model(username="john_doe", display_name="John Doe", email="john@example.com", password="SecurePass123")
        assert user.username == "john_doe"
        assert user.display_name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password == "SecurePass123"
        assert user.slug == "john-doe"

    def test_valid_user_without_display_name(self, register_user_model):
        """Test creating a valid user without display name."""
        user = register_user_model(username="jane_doe", email="jane@example.com", password="ValidPass456")
        assert user.username == "jane_doe"
        assert user.display_name is None
        assert user.email == "jane@example.com"

    def test_slug_generation(self, register_user_model):
        """Test that slug is correctly generated from username."""
        user = register_user_model(username="test_user_123", email="test@example.com", password="Password123")
        assert user.slug == "test-user-123"


class TestUsernameValidation:
    """Test suite for username validation rules."""

    def test_username_too_short(self, register_user_model):
        """Test that username shorter than 3 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="ab", email="test@example.com", password="Password123")
        assert "at least 3 items" in str(exc_info.value)

    def test_username_too_long(self, register_user_model):
        """Test that username longer than 50 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="a" * 51, email="test@example.com", password="Password123")
        assert "at most 50 items" in str(exc_info.value)

    def test_username_with_spaces_rejected(self, register_user_model):
        """Test that usernames with spaces are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="john doe", email="test@example.com", password="Password123")
        assert "lowercase letters, numbers, underscores, and hyphens" in str(exc_info.value)

    def test_username_with_special_characters_rejected(self, register_user_model):
        """Test that usernames with special characters are rejected."""
        invalid_usernames = ["john@doe", "john.doe!", "john$doe", "john#doe"]
        for username in invalid_usernames:
            with pytest.raises(ValidationError) as exc_info:
                register_user_model(username=username, email="test@example.com", password="Password123")
            assert "lowercase letters, numbers, underscores, and hyphens" in str(exc_info.value)

    def test_username_normalized_to_lowercase(self, register_user_model):
        """Test that username is automatically converted to lowercase."""
        user = register_user_model(username="JohnDoe", email="test@example.com", password="Password123")
        assert user.username == "johndoe"

    def test_username_whitespace_trimmed(self, register_user_model):
        """Test that leading/trailing whitespace is trimmed from username."""
        user = register_user_model(username="  john_doe  ", email="test@example.com", password="Password123")
        assert user.username == "john_doe"

    def test_username_with_valid_characters(self, register_user_model):
        """Test that valid username characters are accepted."""
        valid_usernames = ["john_doe", "john-doe", "john123", "user_name_123"]
        for username in valid_usernames:
            user = register_user_model(username=username, email="test@example.com", password="Password123")
            assert user.username == username.lower()


class TestDisplayNameValidation:
    """Test suite for display_name validation rules."""

    def test_display_name_too_short(self, register_user_model):
        """Test that display name shorter than 3 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", display_name="ab", email="test@example.com", password="Password123")
        assert "at least 3 items" in str(exc_info.value)

    def test_display_name_too_long(self, register_user_model):
        """Test that display name longer than 50 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", display_name="a" * 51, email="test@example.com", password="Password123")
        assert "at most 50 items" in str(exc_info.value)

    def test_display_name_allows_spaces(self, register_user_model):
        """Test that display name can contain spaces."""
        user = register_user_model(username="johndoe", display_name="John Doe", email="test@example.com", password="Password123")
        assert user.display_name == "John Doe"

    def test_display_name_whitespace_trimmed(self, register_user_model):
        """Test that leading/trailing whitespace is trimmed from display name."""
        user = register_user_model(username="johndoe", display_name="  John Doe  ", email="test@example.com", password="Password123")
        assert user.display_name == "John Doe"

    def test_display_name_empty_string_becomes_none(self, register_user_model):
        """Test that empty string for display name becomes None."""
        user = register_user_model(username="johndoe", display_name="", email="test@example.com", password="Password123")
        assert user.display_name is None

    def test_display_name_only_whitespace_becomes_none(self, register_user_model):
        """Test that display name with only whitespace becomes None."""
        user = register_user_model(username="johndoe", display_name="   ", email="test@example.com", password="Password123")
        assert user.display_name is None

    def test_display_name_is_none(self, register_user_model):
        """Test that display name with only whitespace becomes None."""
        user = register_user_model(username="johndoe", display_name=None, email="test@example.com", password="Password123")
        assert user.display_name is None

    def test_display_name_default_none(self, register_user_model):
        """Test that display name with only whitespace becomes None."""
        user = register_user_model(username="johndoe", email="test@example.com", password="Password123")
        assert user.display_name is None


class TestEmailValidation:
    """Test suite for email validation rules."""

    def test_valid_email_formats(self, register_user_model):
        """Test that various valid email formats are accepted."""
        valid_emails = ["user@example.com", "user.name@example.com", "user+tag@example.co.uk", "user_name@subdomain.example.com", "a@b.c"]
        for email in valid_emails:
            user = register_user_model(username="johndoe", email=email, password="Password123")
            assert user.email == email

    def test_invalid_email_formats(self, register_user_model):
        """Test that invalid email formats are rejected."""
        invalid_emails = ["notanemail", "@example.com", "user@", "user @example.com", "user@.com"]
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                register_user_model(username="johndoe", email=email, password="Password123")

    def test_email_too_long(self, register_user_model):
        """Test that email longer than 100 items is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="a" * 129 + "@example.com", password="Password123")
        assert "at most 128 items" in str(exc_info.value)

    def test_email_whitespace_trimmed(self, register_user_model):
        """Test that leading/trailing whitespace is trimmed from email."""
        user = register_user_model(username="johndoe", email="  user@example.com  ", password="Password123")
        assert user.email == "user@example.com"


class TestPasswordValidation:
    """Test suite for password validation rules."""

    def test_valid_password(self, register_user_model):
        """Test that a valid password is accepted."""
        user = register_user_model(username="johndoe", email="test@example.com", password="ValidPass123")
        assert user.password == "ValidPass123"

    def test_password_too_short(self, register_user_model):
        """Test that password shorter than 8 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com", password="Pass1")
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_too_long(self, register_user_model):
        """Test that password longer than 128 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com", password="P" + "a" * 130 + "1")
        assert "maximum length is 128 characters" in str(exc_info.value)

    def test_password_missing_uppercase(self, register_user_model):
        """Test that password without uppercase letter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com", password="password123")
        assert "uppercase letter" in str(exc_info.value)

    def test_password_missing_lowercase(self, register_user_model):
        """Test that password without lowercase letter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com", password="PASSWORD123")
        assert "lowercase letter" in str(exc_info.value)

    def test_password_missing_number(self, register_user_model):
        """Test that password without number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com", password="PasswordOnly")
        assert "number" in str(exc_info.value)

    def test_password_with_special_characters(self, register_user_model):
        """Test that password with special characters is accepted."""
        user = register_user_model(username="johndoe", email="test@example.com", password="Pass@word123!")
        assert user.password == "Pass@word123!"

    def test_password_excluded_from_dump(self, register_user_model):
        """Test that password is excluded from model dump."""
        user = register_user_model(username="johndoe", email="test@example.com", password="Password123")
        dumped = user.model_dump()
        assert "password" not in dumped


class TestModelDump:
    """Test suite for model serialization."""

    def test_model_dump_excludes_password(self, register_user_model):
        """Test that password field is excluded from model dump."""
        user = register_user_model(username="johndoe", display_name="John Doe", email="test@example.com", password="Password123")
        dumped = user.model_dump()
        assert dumped == {"username": "johndoe", "display_name": "John Doe", "email": "test@example.com", "slug": "johndoe"}

    def test_model_dump_with_none_display_name(self, register_user_model):
        """Test model dump when display_name is None."""
        user = register_user_model(username="johndoe", email="test@example.com", password="Password123")
        dumped = user.model_dump()
        assert dumped["display_name"] is None
        assert "password" not in dumped


class TestMissingRequiredFields:
    """Test suite for missing required fields."""

    def test_missing_username(self, register_user_model):
        """Test that missing username is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(email="test@example.com", password="Password123")
        assert "username" in str(exc_info.value)

    def test_username_is_none(self, register_user_model):
        """Test that None username is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username=None, email="test@example.com", password="Password123")
        assert "username" in str(exc_info.value)

    def test_missing_email(self, register_user_model):
        """Test that missing email is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", password="Password123")
        assert "email" in str(exc_info.value)

    def test_missing_password(self, register_user_model):
        """Test that missing password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            register_user_model(username="johndoe", email="test@example.com")
        assert "password" in str(exc_info.value)

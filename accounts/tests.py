from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from rest_framework import status
from rest_framework.test import APIClient

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

BASE_URL = "/api/accounts/"

# Test email URLs used instead of real frontend URLs.
TEST_EMAIL_SETTINGS = {
    "EMAIL_VERIFICATION_URL": (
        "http://localhost:5173/verify-email/?uid={uid}&token={token}"
    ),
    "PASSWORD_RESET_URL": (
        "http://localhost:5173/reset-password/?uid={uid}&token={token}"
    ),
}


# ============================================================
# Registration Tests
# ============================================================
@override_settings(**TEST_EMAIL_SETTINGS)
class RegisterTests(TestCase):

    def setUp(self):
        # Clear throttle records from previous tests.
        cache.clear()

        self.client = APIClient()
        self.register_url = BASE_URL + "register/"

        self.valid_data = {
            "email": "test@example.com",
            "display_name": "Test User",
            "password": "StrongPass!9284",
            "confirm_password": "StrongPass!9284",
        }

    def test_user_can_register(self):
        response = self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(email="test@example.com").exists()
        )

    def test_registered_user_is_inactive(self):
        self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        user = User.objects.get(email="test@example.com")

        self.assertFalse(user.is_active)

    def test_password_is_hashed(self):
        self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        user = User.objects.get(email="test@example.com")

        self.assertNotEqual(user.password, self.valid_data["password"])
        self.assertTrue(user.check_password(self.valid_data["password"]))

    def test_registration_sends_verification_email(self):
        self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "Verify your API Inspector account",
        )

    def test_registration_with_existing_email_fails(self):
        User.objects.create_user(
            email="test@example.com",
            password="StrongPass!9284",
        )

        response = self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_mismatched_passwords_fails(self):
        self.valid_data["confirm_password"] = "DifferentPass!9284"

        response = self.client.post(
            self.register_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# Login Tests
# ============================================================

# Tests JWT token generation, invalid credentials,
# and refresh token functionality.

class LoginTests(TestCase):

    def setUp(self):
        # Clear throttle records from previous tests.
        cache.clear()

        self.client = APIClient()
        self.login_url = BASE_URL + "login/"

        self.password = "StrongPass!9284"

        self.user = User.objects.create_user(
            email="test@example.com",
            password=self.password,
            is_active=True,
        )

    def test_user_can_login(self):
        response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": "WrongPassword!123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_refresh_access_token(self):
        login_response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        refresh_token = login_response.data["refresh"]

        response = self.client.post(
            BASE_URL + "token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


# ============================================================
# Email Verification Tests
# ============================================================

# Tests email verification, invalid tokens,
# missing verification data, and inactive account restrictions.

class EmailVerificationTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.password = "StrongPass!9284"

        self.user = User.objects.create_user(
            email="test@example.com",
            password=self.password,
            is_active=False,
        )

        self.verify_url = BASE_URL + "verify-email/"

        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_user_can_verify_email(self):
        response = self.client.post(
            self.verify_url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_verification_with_invalid_token_fails(self):
        response = self.client.post(
            self.verify_url,
            {
                "uid": self.uid,
                "token": "invalid-token",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verification_with_invalid_uid_fails(self):
        response = self.client.post(
            self.verify_url,
            {
                "uid": "invalid-uid",
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verification_requires_uid_and_token(self):
        response = self.client.post(
            self.verify_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_verified_user_receives_message(self):
        self.user.is_active = True
        self.user.save()

        response = self.client.post(
            self.verify_url,
            {
                "uid": self.uid,
                "token": self.token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "Email has already been verified.",
        )

    def test_inactive_user_cannot_login(self):
        response = self.client.post(
            BASE_URL + "login/",
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verified_user_can_login(self):
        self.user.is_active = True
        self.user.save()

        response = self.client.post(
            BASE_URL + "login/",
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================
# User Profile Tests
# ============================================================

# Tests authenticated access to the current user's profile
# and prevents unauthorized access.

class MeViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass!9284",
            display_name="Test User",
            is_active=True,
        )

        self.me_url = BASE_URL + "me/"

    def test_authenticated_user_can_view_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["display_name"], "Test User")

    def test_unauthenticated_user_cannot_view_profile(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_can_only_access_own_profile(self):
        another_user = User.objects.create_user(
            email="another@example.com",
            password="StrongPass!9284",
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["email"], another_user.email)


# ============================================================
# Change Password Tests
# ============================================================

# Tests password changes, current password validation,
# password confirmation, and password strength requirements.

class ChangePasswordTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.old_password = "StrongPass!9284"

        self.user = User.objects.create_user(
            email="test@example.com",
            password=self.old_password,
            is_active=True,
        )

        self.change_password_url = BASE_URL + "change-password/"

        self.client.force_authenticate(user=self.user)

        self.valid_data = {
            "old_password": self.old_password,
            "new_password": "NewStrongPass!9284",
            "confirm_new_password": "NewStrongPass!9284",
        }

    def test_user_can_change_password(self):
        response = self.client.post(
            self.change_password_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("NewStrongPass!9284")
        )

    def test_change_password_with_wrong_old_password_fails(self):
        self.valid_data["old_password"] = "WrongPassword!123"

        response = self.client.post(
            self.change_password_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_with_mismatched_passwords_fails(self):
        self.valid_data["confirm_new_password"] = "DifferentPass!123"

        response = self.client.post(
            self.change_password_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_user_cannot_change_password(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.change_password_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_weak_password_is_rejected(self):
        self.valid_data["new_password"] = "123"
        self.valid_data["confirm_new_password"] = "123"

        response = self.client.post(
            self.change_password_url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# Login Rate Limiting Tests
# ============================================================

# Ensures repeated login attempts are limited
# to protect accounts against brute-force attempts.

class LoginRateLimitTests(TestCase):

    def setUp(self):
        cache.clear()

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass!9284",
            is_active=True,
        )

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
            "DEFAULT_THROTTLE_RATES": {
                "login": "5/min",
            },
        }
    )
    def test_login_rate_limit(self):
        url = BASE_URL + "login/"

        # Send requests until the rate limit is exceeded.
        for _ in range(5):
            self.client.post(
                url,
                {
                    "email": self.user.email,
                    "password": "WrongPassword!123",
                },
                format="json",
            )

        response = self.client.post(
            url,
            {
                "email": self.user.email,
                "password": "WrongPassword!123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


# ============================================================
# Password Reset Tests
# ============================================================

# Tests password reset email delivery, token validation,
# password updates, and invalid reset requests.

@override_settings(**TEST_EMAIL_SETTINGS)
class PasswordResetTests(TestCase):

    def setUp(self):
        # Clear throttle records from previous tests.
        cache.clear()

        self.client = APIClient()

        self.password = "StrongPass!9284"

        self.user = User.objects.create_user(
            email="test@example.com",
            password=self.password,
            is_active=True,
        )

        self.reset_url = BASE_URL + "password-reset/"
        self.confirm_url = BASE_URL + "password-reset/confirm/"

    def test_password_reset_sends_email(self):
        response = self.client.post(
            self.reset_url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            mail.outbox[0].subject,
            "Reset your API Inspector password",
        )

    def test_password_reset_with_unknown_email_does_not_send_email(self):
        response = self.client.post(
            self.reset_url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_returns_generic_response(self):
        response = self.client.post(
            self.reset_url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.data["detail"],
            "If an active account exists with this email, "
            "a password reset link has been sent.",
        )

    def test_password_reset_with_empty_email_fails(self):
        response = self.client.post(
            self.reset_url,
            {"email": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password("NewStrongPass!9284")
        )

    def test_password_reset_confirm_with_invalid_token_fails(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": "invalid-token",
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_with_invalid_uid_fails(self):
        response = self.client.post(
            self.confirm_url,
            {
                "uid": "invalid-uid",
                "token": "invalid-token",
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_requires_all_fields(self):
        response = self.client.post(
            self.confirm_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_with_mismatched_passwords_fails(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "DifferentPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_with_weak_password_fails(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": "123",
                "confirm_new_password": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_old_reset_token_becomes_invalid_after_password_change(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # Changing the password invalidates previously generated tokens.
        self.user.set_password("AnotherStrongPass!9284")
        self.user.save()

        response = self.client.post(
            self.confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# Logout Tests
# ============================================================

# Tests refresh token blacklisting and ensures users
# cannot revoke another user's refresh token.

class LogoutTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass!9284",
            is_active=True,
        )

        self.logout_url = BASE_URL + "logout/"

        self.refresh_token = str(
            RefreshToken.for_user(self.user)
        )

        self.client.force_authenticate(user=self.user)

    def test_user_can_logout(self):
        response = self.client.post(
            self.logout_url,
            {"refresh": self.refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Confirm that the refresh token has been blacklisted.
        with self.assertRaises(TokenError):
            RefreshToken(self.refresh_token)

    def test_unauthenticated_user_cannot_logout(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.logout_url,
            {"refresh": self.refresh_token},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_refresh_token(self):
        response = self.client.post(
            self.logout_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_logout_another_users_refresh_token(self):
        another_user = User.objects.create_user(
            email="another@example.com",
            password="StrongPass!9284",
            is_active=True,
        )

        another_refresh_token = str(
            RefreshToken.for_user(another_user)
        )

        response = self.client.post(
            self.logout_url,
            {"refresh": another_refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
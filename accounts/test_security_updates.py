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

from .views import blacklist_user_refresh_tokens


User = get_user_model()

BASE_URL = "/api/accounts/"

TEST_EMAIL_SETTINGS = {
    "EMAIL_VERIFICATION_URL": (
        "http://localhost:5173/verify-email/?uid={uid}&token={token}"
    ),
    "PASSWORD_RESET_URL": (
        "http://localhost:5173/reset-password/?uid={uid}&token={token}"
    ),
}


# ============================================================
# Refresh Token Revocation Tests
# ============================================================

class RefreshTokenRevocationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.password = "StrongPass!9284"

        self.user = User.objects.create_user(
            email="test@example.com",
            password=self.password,
            is_active=True,
        )

    def test_password_change_blacklists_existing_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.user)

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            BASE_URL + "change-password/",
            {
                "old_password": self.password,
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_password_reset_blacklists_existing_refresh_tokens(self):
        refresh = RefreshToken.for_user(self.user)

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            BASE_URL + "password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "new_password": "NewStrongPass!9284",
                "confirm_new_password": "NewStrongPass!9284",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.assertRaises(TokenError):
            RefreshToken(str(refresh))

    def test_blacklist_helper_revokes_all_user_tokens(self):
        first_token = RefreshToken.for_user(self.user)
        second_token = RefreshToken.for_user(self.user)

        blacklist_user_refresh_tokens(self.user)

        with self.assertRaises(TokenError):
            RefreshToken(str(first_token))

        with self.assertRaises(TokenError):
            RefreshToken(str(second_token))


# ============================================================
# Registration Email Failure Tests
# ============================================================

@override_settings(**TEST_EMAIL_SETTINGS)
class RegistrationEmailFailureTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.data = {
            "email": "test@example.com",
            "display_name": "Test User",
            "password": "StrongPass!9284",
            "confirm_password": "StrongPass!9284",
        }

    def test_user_is_not_created_when_email_sending_fails(self):
        from unittest.mock import patch

        with patch(
            "accounts.views.send_mail",
            side_effect=Exception("SMTP error"),
        ):
            with self.assertRaises(Exception):
                self.client.post(
                    BASE_URL + "register/",
                    self.data,
                    format="json",
                )

        self.assertFalse(
            User.objects.filter(email="test@example.com").exists()
        )


# ============================================================
# Resend Verification Email Tests
# ============================================================

@override_settings(**TEST_EMAIL_SETTINGS)
class ResendVerificationTests(TestCase):

    def setUp(self):
        cache.clear()

        self.client = APIClient()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="StrongPass!9284",
            is_active=False,
        )

        self.url = BASE_URL + "resend-verification/"

    def test_unverified_user_can_request_another_email(self):
        response = self.client.post(
            self.url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_returns_generic_response(self):
        response = self.client.post(
            self.url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_verified_user_does_not_receive_another_email(self):
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.url,
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)
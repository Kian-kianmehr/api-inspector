from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import (
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)

from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
)
from .throttles import LoginRateThrottle


User = get_user_model()


# ============================================================
# Shared Helpers
# ============================================================

def encode_user_id(user):
    """Encode a user's primary key for email links."""
    return urlsafe_base64_encode(str(user.pk).encode())


def send_verification_email(user):
    """Send an email verification link to a user."""
    uid = encode_user_id(user)
    token = default_token_generator.make_token(user)

    verification_url = settings.EMAIL_VERIFICATION_URL.format(
        uid=uid,
        token=token,
    )

    send_mail(
        subject="Verify your API Inspector account",
        message=(
            f"Hello {user.display_name or user.email},\n\n"
            "Please verify your email address using the link below:\n\n"
            f"{verification_url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    """Send a password reset link to a user."""
    uid = encode_user_id(user)
    token = default_token_generator.make_token(user)

    reset_url = settings.PASSWORD_RESET_URL.format(
        uid=uid,
        token=token,
    )

    send_mail(
        subject="Reset your API Inspector password",
        message=(
            "We received a request to reset your password.\n\n"
            f"Use the link below:\n\n{reset_url}\n\n"
            "If you did not request a password reset, "
            "you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def blacklist_user_refresh_tokens(user):
    """Blacklist every outstanding refresh token belonging to a user."""
    outstanding_tokens = OutstandingToken.objects.filter(user=user)

    for outstanding_token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(
            token=outstanding_token,
        )


# ============================================================
# Registration
# ============================================================

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def perform_create(self, serializer):
        # Roll back account creation if sending the verification email fails.
        with transaction.atomic():
            user = serializer.save()
            send_verification_email(user)


class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resend_verification"

    def post(self, request):
        email = serializers.EmailField().run_validation(
            request.data.get("email")
        )

        user = User.objects.filter(
            email__iexact=email,
            is_active=False,
        ).first()

        # Keep the response generic to avoid revealing account existence.
        if user:
            send_verification_email(user)

        return Response(
            {
                "detail": (
                    "If an unverified account exists with this email, "
                    "a verification link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# Authentication
# ============================================================

class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]


# ============================================================
# User Profile
# ============================================================

class MeView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ============================================================
# Change Password
# ============================================================

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Revoke existing refresh tokens after a successful password change.
        blacklist_user_refresh_tokens(user)

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Password Reset Request
# ============================================================

class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = serializers.EmailField().run_validation(
            request.data.get("email")
        )

        users = User.objects.filter(
            email__iexact=email,
            is_active=True,
        )

        for user in users:
            send_password_reset_email(user)

        return Response(
            {
                "detail": (
                    "If an active account exists with this email, "
                    "a password reset link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# Password Reset Confirmation
# ============================================================

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Revoke all existing refresh tokens after password reset.
        blacklist_user_refresh_tokens(user)

        return Response(
            {"detail": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Email Verification
# ============================================================

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify_email"

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")

        if not uid or not token:
            return Response(
                {"detail": "UID and token are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_active:
            return Response(
                {"detail": "Email has already been verified."},
                status=status.HTTP_200_OK,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired verification link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=["is_active"])

        return Response(
            {"detail": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Logout
# ============================================================

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            token_user_id = token.get(
                settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
            )

            if str(token_user_id) != str(request.user.pk):
                return Response(
                    {"detail": "Invalid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token.blacklist()

        except (TokenError, KeyError, TypeError):
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
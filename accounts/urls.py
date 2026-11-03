from django.urls import path

from .views import (
    RegisterView,
    ResendVerificationEmailView,
    LoginView,
    RefreshTokenView,
    MeView,
    ChangePasswordView,
    PasswordResetView,
    PasswordResetConfirmView,
    VerifyEmailView,
    LogoutView,
)


urlpatterns = [
    # Registration
    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),
    path(
        "resend-verification/",
        ResendVerificationEmailView.as_view(),
        name="resend-verification",
    ),

    # Authentication
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "token/refresh/",
        RefreshTokenView.as_view(),
        name="token-refresh",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    # User Profile
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),

    # Password Reset
    path(
        "password-reset/",
        PasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),

    # Email Verification
    path(
        "verify-email/",
        VerifyEmailView.as_view(),
        name="verify-email",
    ),
]
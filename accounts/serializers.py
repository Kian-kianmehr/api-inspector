from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import serializers


User = get_user_model()


# ============================================================
# Registration
# ============================================================

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "display_name",
            "password",
            "confirm_password",
        )

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        user = User(
            email=attrs.get("email"),
            display_name=attrs.get("display_name", ""),
        )

        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "password": error.messages
            })

        attrs.pop("confirm_password")

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
            is_active=False,
        )


# ============================================================
# User Profile
# ============================================================

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "created_at",
            "is_active",
        )
        read_only_fields = fields


# ============================================================
# Change Password
# ============================================================

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({
                "old_password": "Current password is incorrect."
            })

        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": "Passwords do not match."
            })

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "new_password": error.messages
            })

        return attrs


# ============================================================
# Password Reset Confirmation
# ============================================================

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({
                "confirm_new_password": "Passwords do not match."
            })

        try:
            user_id = force_str(
                urlsafe_base64_decode(attrs["uid"])
            )
            user = User.objects.get(
                pk=user_id,
                is_active=True,
            )
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                "detail": "Invalid or expired reset link."
            })

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({
                "detail": "Invalid or expired reset link."
            })

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({
                "new_password": error.messages
            })

        attrs["user"] = user

        return attrs
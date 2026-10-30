from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .password_reset import INVALID_LINK_MESSAGE, token_is_valid, user_from_uid


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetTokenSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        if not token_is_valid(attrs["uid"], attrs["token"]):
            raise serializers.ValidationError({"token": [INVALID_LINK_MESSAGE]})
        return attrs


class PasswordResetConfirmSerializer(PasswordResetTokenSerializer):
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = user_from_uid(attrs["uid"])
        validate_password(attrs["password"], user=user)
        return attrs

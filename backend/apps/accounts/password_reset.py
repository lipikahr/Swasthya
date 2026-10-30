"""Token-based password reset. Tokens are time-limited and become invalid after use."""

import logging

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError

from .models import User

logger = logging.getLogger(__name__)
GENERIC_REQUEST_MESSAGE = (
    "If an account exists for that email address, a reset link has been sent."
)
INVALID_LINK_MESSAGE = "This reset link is invalid or has expired."
token_generator = PasswordResetTokenGenerator()


def request_reset(email: str) -> str:
    normalized = (email or "").strip().lower()
    user = User.objects.filter(email=normalized, is_active=True).first()
    if user is not None:
        try:
            _send_reset_email(user)
        except Exception:
            # Delivery failures must not change the HTTP response; a 500 for
            # known addresses would reveal that an account exists.
            logger.exception("Password reset email could not be delivered to a matching account.")
    return GENERIC_REQUEST_MESSAGE


def confirm_reset(uid: str, token: str, password: str) -> str:
    user = user_from_uid(uid)
    if user is None or not token_generator.check_token(user, token):
        raise ValidationError({"token": [INVALID_LINK_MESSAGE]})
    user.set_password(password)
    user.save(update_fields=["password"])
    return "Your password has been reset. You can log in now."


def token_is_valid(uid: str, token: str) -> bool:
    user = user_from_uid(uid)
    return bool(user and token_generator.check_token(user, token))


def user_from_uid(uid: str):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        return User.objects.filter(pk=user_id, is_active=True).first()
    except (ValueError, TypeError, OverflowError, User.DoesNotExist):
        return None


def _send_reset_email(user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    origin = str(getattr(settings, "FRONTEND_URL", None) or "http://127.0.0.1:5173").rstrip("/")
    link = f"{origin}/reset-password?uid={uid}&token={token}"
    body = (
        "We received a request to reset the Swasthya password for this email address.\n\n"
        f"Open this link within 24 hours to choose a new password:\n{link}\n\n"
        "The link can be used once. If you did not ask for this, you can ignore the message."
    )
    send_mail(
        subject="Reset your Swasthya password",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "Swasthya <noreply@localhost>"),
        recipient_list=[user.email],
        fail_silently=False,
    )

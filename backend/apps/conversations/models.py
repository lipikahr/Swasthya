from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class InputType(models.TextChoices):
        TEXT = "text", "Text"
        VOICE = "voice", "Voice"
        IMAGE = "image", "Image"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    input_type = models.CharField(max_length=16, choices=InputType.choices, default=InputType.TEXT)

    class Meta:
        ordering = ["timestamp", "id"]


class AgentAction(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="actions")
    action_type = models.CharField(max_length=64)
    tool_name = models.CharField(max_length=64)
    tool_input = models.JSONField()
    tool_output = models.JSONField()
    status = models.CharField(max_length=32)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp", "id"]

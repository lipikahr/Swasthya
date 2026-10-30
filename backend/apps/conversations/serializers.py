from rest_framework import serializers

from .models import AgentAction, Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "timestamp", "input_type")


class AgentActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentAction
        fields = ("id", "action_type", "tool_name", "tool_input", "tool_output", "status", "timestamp")


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("id", "created_at", "updated_at")


def is_catalogue_dump(content: str) -> bool:
    """A clarification that lists a catalogue slice is not a conversation turn to show."""
    text = content or ""
    if not text.startswith("Which food did you mean?"):
        return False
    return text.count(",") >= 3


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    actions = AgentActionSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ("messages", "actions")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["messages"] = [message for message in data["messages"] if not is_catalogue_dump(message.get("content") or "")]
        return data

from django.contrib import admin

from .models import AgentAction, Conversation, MealDraft, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(MealDraft)
class MealDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "user", "status", "meal_type", "updated_at")


@admin.register(AgentAction)
class AgentActionAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "tool_name", "status", "timestamp")

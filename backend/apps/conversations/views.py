from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation
from .serializers import ConversationDetailSerializer, ConversationSerializer


class ConversationListView(APIView):
    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)
        return Response({"results": ConversationSerializer(conversations, many=True).data})


class ConversationDetailView(APIView):
    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.filter(user=request.user).prefetch_related("messages", "actions"),
            pk=conversation_id,
        )
        return Response(ConversationDetailSerializer(conversation).data)

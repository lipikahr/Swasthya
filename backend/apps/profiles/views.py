from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProfile
from .serializers import PROFILE_FIELDS, ProfileSerializer

EMPTY_PROFILE = {
    "date_of_birth": None,
    "sex": "",
    "height_cm": None,
    "weight_kg": None,
    "activity_level": "",
    "goal": "",
    "allergies_status": "",
    "allergies": [],
    "dislikes": [],
    "diet_pattern": "",
    "preferred_cuisines": [],
    "preferred_language": "en",
    "appearance": "light",
    "restrictions": [],
    "likes": [],
    "notes": "",
    "autoplay_replies": False,
}


class ProfileView(APIView):
    def get(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response(EMPTY_PROFILE)
        return Response(ProfileSerializer(profile).data)

    def put(self, request):
        return self._save(request, partial=False)

    def patch(self, request):
        return self._save(request, partial=True)

    def _save(self, request, partial: bool):
        if not partial:
            missing = [field for field in PROFILE_FIELDS if field not in request.data]
            if missing:
                raise ValidationError({field: ["This field is required."] for field in missing})
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

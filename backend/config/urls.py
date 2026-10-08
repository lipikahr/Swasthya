from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/profile/", include("apps.profiles.urls")),
    path("api/targets/", include("apps.targets.urls")),
    path("api/foods/", include("apps.nutrition.urls")),
    path("api/meals/", include("apps.meals.urls")),
    path("api/dashboard/", include("apps.progress.dashboard_urls")),
    path("api/progress/", include("apps.progress.urls")),
    path("api/streaks/", include("apps.progress.streak_urls")),
    path("api/conversations/", include("apps.conversations.urls")),
    path("api/agent/", include("apps.agent.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

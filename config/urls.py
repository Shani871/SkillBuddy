from django.contrib import admin
from django.db import connection
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views import defaults as default_views
from django.views.static import serve
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog
from django.urls import re_path

admin.site.site_header = "SkyLearn Admin"


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("", include("core.urls")),
    path("jet/", include("jet.urls", "jet")),  # Django JET URLS
    path(
        "jet/dashboard/", include("jet.dashboard.urls", "jet-dashboard")
    ),  # Django JET dashboard URLS
    path("accounts/", include("accounts.urls")),
    path("programs/", include("course.urls")),
    path("result/", include("result.urls")),
    path("search/", include("search.urls")),
    path("quiz/", include("quiz.urls")),
    path("payments/", include("payments.urls")),
    path("emotions/", include("emotions.urls")),
    path("ai-tutor/", include("ai_tutor.urls")),
    path("", include("chatbot.urls")),
)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "SERVE_MEDIA_FILES", False):
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]

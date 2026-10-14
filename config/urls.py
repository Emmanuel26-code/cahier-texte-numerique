from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("apps.comptes.urls")),
    path("documents/", include("apps.documents.urls")),
    path("", TemplateView.as_view(template_name="accueil.html"), name="accueil"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
